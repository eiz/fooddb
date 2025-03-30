import os
import json
import sqlite3
import concurrent.futures
import logging
import time
from typing import List, Optional, Tuple

from openai import OpenAI
import sqlite_vec

# Configure logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("fooddb.embeddings")

# Wrapper for database operations with query logging
def execute_query(conn, query, params=None, many=False):
    """Execute SQL with logging"""
    logger.info(f"SQL: {query}")
    cursor = conn.cursor()
    if many:
        return cursor.executemany(query, params)
    elif params:
        return cursor.execute(query, params)
    else:
        return cursor.execute(query)

# Log connection operations
def connect_db(db_path):
    """Connect to the database with logging and loading the sqlite-vec extension"""
    if db_path.startswith('sqlite:///'):
        sqlite_path = db_path[10:]
    else:
        sqlite_path = db_path
    
    logger.info(f"SQL: Opening connection to {sqlite_path}")
    conn = sqlite3.connect(sqlite_path)
    
    # Always load the sqlite-vec extension for all connections
    conn.enable_load_extension(True)
    try:
        sqlite_vec.load(conn)
        logger.debug("Loaded sqlite-vec extension")
    except Exception as e:
        logger.warning(f"Could not load sqlite-vec extension: {e}")
    
    return conn

def close_db(conn):
    """Close database connection with logging"""
    logger.info("SQL: Closing connection")
    conn.close()

# Initialize OpenAI client if API key is available
client = None
if os.environ.get("OPENAI_API_KEY"):
    client = OpenAI()

# Embedding dimensions for the model we'll use
EMBEDDING_DIMS = 1536  # For text-embedding-3-small

def setup_vector_db(db_path: str = "fooddb.sqlite") -> None:
    """Set up the vector database with necessary tables and indexes."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    
    # Verify the extension loaded correctly
    cursor = execute_query(conn, "SELECT vec_version()")
    vec_version = cursor.fetchone()[0]
    print(f"Using sqlite-vec version {vec_version}")
    
    # Check if vector table exists, drop and recreate if needed
    execute_query(conn, "DROP TABLE IF EXISTS food_embeddings;")
    execute_query(conn, f"""
    CREATE VIRTUAL TABLE food_embeddings USING vec0(
        embedding FLOAT[{EMBEDDING_DIMS}]
    );
    """)
    print(f"Created food_embeddings virtual table with {EMBEDDING_DIMS} dimensions")
    
    # Check if index exists on fdc_id and create it if not
    cursor = execute_query(conn, "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_food_fdc_id';")
    if not cursor.fetchone():
        # Create index on food.fdc_id to speed up LEFT JOIN queries
        execute_query(conn, "CREATE INDEX IF NOT EXISTS idx_food_fdc_id ON food(fdc_id);")
        print("Created index on food.fdc_id")
    
    # Close connection
    close_db(conn)
    print("Vector database setup complete")


def generate_embedding(text: str, model: str = "text-embedding-3-small") -> Optional[List[float]]:
    """Generate an embedding vector for the given text using OpenAI API."""
    if not client:
        print("Warning: OpenAI client not initialized. Set OPENAI_API_KEY environment variable.")
        return None
    
    try:
        response = client.embeddings.create(
            input=text,
            model=model
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def store_embedding(fdc_id: int, embedding: List[float], model: str, db_path: str = "fooddb.sqlite", conn=None) -> bool:
    """Store an embedding vector in the database."""
    # Allow passing an existing connection to avoid repeated connection setup
    close_conn = False
    if conn is None:
        conn = connect_db(db_path)
        close_conn = True
    
    try:
        # Create a JSON string of the embedding vector
        embedding_json = json.dumps(embedding)
        
        # Store in database - use rowid as fdc_id for the virtual table
        execute_query(
            conn,
            "INSERT OR REPLACE INTO food_embeddings (rowid, embedding) VALUES (?, ?)",
            (fdc_id, embedding_json)
        )
        return True
    except Exception as e:
        logger.error(f"Error storing embedding: {e}")
        return False
    finally:
        if close_conn:
            close_db(conn)


def search_by_embedding(
    query_embedding: List[float], 
    limit: int = 10, 
    db_path: str = "fooddb.sqlite"
) -> List[Tuple[int, float]]:
    """
    Search for foods using vector similarity with KNN.
    
    Args:
        query_embedding: The embedding vector to search for
        limit: Maximum number of results to return
        db_path: Path to SQLite database
    
    Returns:
        List of tuples (fdc_id, similarity_score)
    """
    conn = connect_db(db_path)
    
    try:
        
        # Convert embedding to JSON string for the MATCH query
        query_json = json.dumps(query_embedding)
        
        # Search using KNN MATCH syntax for faster retrieval
        # The 'distance' from vec0 is L2 distance, not cosine, so we convert to similarity
        cursor = execute_query(conn, """
        SELECT 
            rowid,
            1 - (distance / 2) AS similarity
        FROM 
            food_embeddings
        WHERE 
            embedding MATCH ?
        ORDER BY 
            distance
        LIMIT ?
        """, (query_json, limit))
        
        return cursor.fetchall()
    except Exception as e:
        print(f"Error searching by embedding: {e}")
        return []
    finally:
        close_db(conn)


def process_embedding_batch(
    batch: List[Tuple[int, str]], 
    model: str, 
    db_path: str
) -> int:
    """
    Process a single batch of embeddings.
    
    Args:
        batch: List of (fdc_id, description) tuples
        model: OpenAI embedding model to use
        db_path: Path to SQLite database
        
    Returns:
        Number of successfully processed embeddings
    """
    batch_start_time = time.time()
    
    if not client or not batch:
        logger.warning("OpenAI client not initialized or empty batch")
        return 0
    
    logger.info(f"Processing batch of {len(batch)} foods with model {model}")
    
    # Create a single connection for the entire batch
    conn = connect_db(db_path)
    
    try:
        
        # Prepare texts
        texts = [food[1] for food in batch]
        fdc_ids = [food[0] for food in batch]
        
        # Generate embeddings
        logger.debug(f"Sending API request for {len(texts)} texts")
        api_start_time = time.time()
        response = client.embeddings.create(
            input=texts,
            model=model
        )
        api_duration = time.time() - api_start_time
        logger.info(f"API request completed in {api_duration:.2f} seconds")
        
        # Store embeddings - use bulk insert for efficiency
        execute_query(conn, "BEGIN TRANSACTION")
        success_count = 0
        store_start_time = time.time()
        
        try:
            # Prepare all embeddings for bulk insert
            values_to_insert = []
            for j, embedding_data in enumerate(response.data):
                fdc_id = fdc_ids[j]
                embedding = embedding_data.embedding
                # JSON serialize the embedding vectors for the virtual table
                embedding_json = json.dumps(embedding)
                values_to_insert.append((fdc_id, embedding_json))
            
            # Use executemany for bulk insert - much faster than individual inserts
            execute_query(
                conn,
                "INSERT OR REPLACE INTO food_embeddings (rowid, embedding) VALUES (?, ?)",
                values_to_insert,
                many=True
            )
            success_count = len(values_to_insert)
            
            # Commit all changes at once
            execute_query(conn, "COMMIT")
        except Exception as e:
            logger.error(f"Error in bulk insert: {e}")
            logger.info("SQL: ROLLBACK")
            conn.rollback()
            success_count = 0
                
        store_duration = time.time() - store_start_time
        logger.info(f"Stored {success_count}/{len(batch)} embeddings in {store_duration:.2f} seconds")
        
        batch_duration = time.time() - batch_start_time
        logger.info(f"Batch processing completed in {batch_duration:.2f} seconds")
        return success_count
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        logger.info("SQL: ROLLBACK")
        conn.rollback()
        return 0
    finally:
        close_db(conn)


def generate_batch_embeddings(
    batch_size: int = 1000, 
    model: str = "text-embedding-3-small",
    db_path: str = "fooddb.sqlite",
    parallel: int = 1,
    timeout: int = 600  # Default timeout in seconds (10 minutes)
) -> None:
    """
    Generate embeddings for ALL foods that don't have embeddings yet.
    
    Args:
        batch_size: Number of foods to process in each batch
        model: OpenAI embedding model to use
        db_path: Path to SQLite database
        parallel: Number of parallel API requests to make (1 = sequential)
        timeout: Maximum time to run in seconds (default: 10 minutes)
    """
    start_time = time.time()
    
    if not client:
        logger.warning("OpenAI client not initialized. Set OPENAI_API_KEY environment variable.")
        return
    
    logger.info("Connecting to database")
    conn = connect_db(db_path)
    
    try:
        # First, get a count of how many foods need embeddings
        # Use rowid from virtual table since it represents the fdc_id
        count_query = """
        SELECT COUNT(f.fdc_id)
        FROM food f
        WHERE NOT EXISTS (
            SELECT 1 FROM food_embeddings fe
            WHERE fe.rowid = f.fdc_id
        )
        """
        logger.info("Counting foods without embeddings (this may take a moment)...")
        count_start_time = time.time()
        cursor = execute_query(conn, count_query)
        
        total_missing = cursor.fetchone()[0]
        count_duration = time.time() - count_start_time
        logger.info(f"Count query completed in {count_duration:.2f} seconds")
        
        if total_missing == 0:
            logger.info("No foods found without embeddings.")
            return
        
        logger.info(f"Found {total_missing} foods that need embeddings. Processing all of them.")
        logger.info(f"Using {parallel} parallel request{'s' if parallel > 1 else ''}")
        logger.info(f"Operation will timeout after {timeout} seconds")
        
        # Set up counters for tracking progress
        total_processed = 0
        api_batch_size = 100  # OpenAI recommends smaller batches
        
        # Process in batches until all are done or timeout
        while total_processed < total_missing:
            # Check if we've exceeded the timeout
            if time.time() - start_time > timeout:
                logger.warning(f"Timeout reached after {timeout} seconds. Stopping.")
                break
                
            # Get the next batch of foods without embeddings
            # Use rowid from virtual table since it represents the fdc_id
            batch_query = """
            SELECT f.fdc_id, f.description 
            FROM food f
            WHERE NOT EXISTS (
                SELECT 1 FROM food_embeddings fe
                WHERE fe.rowid = f.fdc_id
            )
            LIMIT ?
            """
            batch_query_start = time.time()
            cursor = execute_query(conn, batch_query, (batch_size,))
            batch_query_duration = time.time() - batch_query_start
            logger.info(f"Batch query completed in {batch_query_duration:.2f} seconds")
            
            foods = cursor.fetchall()
            
            if not foods:
                break
            
            batch_start_time = time.time()
            logger.info(f"Processing batch of {len(foods)} foods ({total_processed}/{total_missing})...")
            
            if parallel <= 1:
                # Sequential processing
                logger.info("Using sequential processing mode")
                for i in range(0, len(foods), api_batch_size):
                    # Check timeout again for each sub-batch
                    if time.time() - start_time > timeout:
                        logger.warning(f"Timeout reached after {timeout} seconds. Stopping.")
                        break
                        
                    sub_batch = foods[i:i+api_batch_size]
                    logger.info(f"Processing sub-batch {i//api_batch_size + 1}/{(len(foods) + api_batch_size - 1)//api_batch_size}")
                    success_count = process_embedding_batch(sub_batch, model, db_path)
                    total_processed += success_count
                    logger.info(f"Processed {i + len(sub_batch)} / {len(foods)} in current batch, {total_processed}/{total_missing} total")
            else:
                # Parallel processing with ThreadPoolExecutor
                logger.info(f"Using parallel processing mode with {parallel} workers")
                batches = [foods[i:i+api_batch_size] for i in range(0, len(foods), api_batch_size)]
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
                    # Submit all tasks
                    logger.info(f"Submitting {len(batches)} tasks to thread pool")
                    futures = [
                        executor.submit(process_embedding_batch, batch, model, db_path)
                        for batch in batches
                    ]
                    
                    # Process results as they complete with timeout
                    remaining_timeout = max(1, timeout - (time.time() - start_time))
                    for i, future in enumerate(concurrent.futures.as_completed(futures, timeout=remaining_timeout)):
                        try:
                            success_count = future.result(timeout=5)  # 5-second timeout for getting result
                            total_processed += success_count
                            # Include time since last completed batch to monitor delays
                            if i > 0:
                                logger.info(f"Completed parallel batch {i+1}/{len(batches)}, {total_processed}/{total_missing} total")
                            else:
                                logger.info(f"Completed first parallel batch, {total_processed}/{total_missing} total")
                        except concurrent.futures.TimeoutError:
                            logger.warning(f"Timed out waiting for batch {i+1} result")
                        except Exception as e:
                            logger.error(f"Error processing batch {i+1}: {e}")
            
            batch_duration = time.time() - batch_start_time
            logger.info(f"Batch completed in {batch_duration:.2f} seconds")
            
        elapsed_time = time.time() - start_time
        logger.info(f"Embedding generation complete. Processed {total_processed} out of {total_missing} foods in {elapsed_time:.2f} seconds.")
    except Exception as e:
        logger.error(f"Error in batch embedding generation: {e}")
        logger.info("SQL: ROLLBACK")
        conn.rollback()
    finally:
        close_db(conn)


def search_food_by_text(
    query: str, 
    limit: int = 10, 
    model: str = "text-embedding-3-small",
    db_path: str = "fooddb.sqlite"
) -> List[Tuple[int, str, float]]:
    """
    Search for foods using semantic text matching with KNN.
    
    Args:
        query: Text query to search for
        limit: Maximum number of results to return
        model: OpenAI embedding model to use
        db_path: Path to SQLite database
    
    Returns:
        List of tuples (fdc_id, description, similarity_score)
    """
    if not client:
        print("Warning: OpenAI client not initialized. Set OPENAI_API_KEY environment variable.")
        return []
    
    start_time = time.time()
    # Generate embedding for the query
    logger.info(f"Generating embedding for query: '{query}'")
    query_embedding = generate_embedding(query, model)
    embedding_time = time.time() - start_time
    logger.info(f"Embedding generation completed in {embedding_time:.2f} seconds")
    
    if not query_embedding:
        return []
    
    conn = connect_db(db_path)
    
    try:
        
        # Convert embedding to JSON string for the MATCH query
        query_json = json.dumps(query_embedding)
        
        # Search using KNN MATCH syntax for faster retrieval 
        query_start_time = time.time()
        cursor = execute_query(conn, """
        SELECT 
            fe.rowid, 
            f.description,
            1 - (distance / 2) AS similarity
        FROM 
            food_embeddings fe
        JOIN 
            food f ON fe.rowid = f.fdc_id
        WHERE 
            embedding MATCH ?
        ORDER BY 
            distance
        LIMIT ?
        """, (query_json, limit))
        
        results = cursor.fetchall()
        query_time = time.time() - query_start_time
        logger.info(f"KNN query completed in {query_time:.2f} seconds, returning {len(results)} results")
        
        total_time = time.time() - start_time
        logger.info(f"Total search time: {total_time:.2f} seconds")
        
        return results
    except Exception as e:
        print(f"Error searching by text: {e}")
        return []
    finally:
        close_db(conn)