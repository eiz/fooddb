# Vector Embeddings Implementation

This document details the vector embedding implementation in FoodDB, which enables semantic food search capabilities.

## Overview

FoodDB uses OpenAI's embedding models to generate vector representations of food descriptions. These vectors are stored in SQLite using the sqlite-vec extension and enable semantic similarity searches.

## Key Components

### Embedding Generation

The embedding generation process is implemented in `fooddb/embeddings.py` with these key features:

#### Parallel Processing
- Uses `concurrent.futures.ThreadPoolExecutor` to make multiple simultaneous API requests
- Configurable number of parallel workers via the `--parallel` CLI option
- Significantly improves performance for large datasets

#### Batch Processing
- Foods are processed in configurable batches (default 1000 items)
- Each batch is further divided into API batches (100 items) for optimal API usage
- Bulk database operations improve insert performance

#### Timeout Control
- Configurable maximum runtime to prevent indefinite execution
- Applies both to the overall process and individual API requests
- Helps manage API costs and system resources

#### SQL Query Logging
- Detailed logging of SQL queries with timestamp information
- Helps identify performance bottlenecks
- Logs connection opening/closing events

#### Database Performance Optimizations
- Uses `NOT EXISTS` subqueries instead of `LEFT JOIN` for better performance
- Creates index on `food.fdc_id` to speed up joins
- Uses `executemany` for bulk insertion of embeddings
- Proper connection pooling and resource management

### Vector Search

The vector search functionality uses the sqlite-vec extension to perform efficient similarity searches:

#### Cosine Similarity
- Uses cosine similarity as the distance metric
- Results are sorted by descending similarity (1.0 = exact match)

#### Query Processing
- Converts text queries to vector embeddings using the same model
- Performs vector similarity search against the stored embeddings

## Implementation Details

### Setup Process

```python
def setup_vector_db(db_path: str = "fooddb.sqlite") -> None:
    """Set up the vector database with necessary tables and indexes."""
    conn = connect_db(db_path)
    # ...
    # Create embeddings table
    # Create indexes
    # ...
```

### Embedding Generation

```python
def generate_batch_embeddings(
    batch_size: int = 1000, 
    model: str = "text-embedding-3-small",
    db_path: str = "fooddb.sqlite",
    parallel: int = 1,
    timeout: int = 600  # Default timeout in seconds
) -> None:
    """Generate embeddings for foods without embeddings."""
    # ...
    # Count foods needing embeddings
    # Process in batches
    # Use parallel or sequential mode depending on configuration
    # ...
```

### Vector Search

```python
def search_food_by_text(
    query: str, 
    limit: int = 10, 
    model: str = "text-embedding-3-small",
    db_path: str = "fooddb.sqlite"
) -> List[Tuple[int, str, float]]:
    """Search for foods using semantic text matching."""
    # ...
    # Generate embedding for query
    # Perform vector similarity search
    # Return matching foods with similarity scores
    # ...
```

## Performance Considerations

### API Throttling
- Batch sizes are chosen to balance performance with API rate limits
- Parallel workers should be tuned based on API quota

### Database Performance
- Indexes are critical for query performance
- The NOT EXISTS approach outperforms LEFT JOIN for finding foods without embeddings
- Connection pooling reduces overhead for batch operations

### Memory Usage
- Embedding vectors (1536 dimensions) are stored efficiently as binary blobs
- Vector similarity operations are handled by sqlite-vec extension

## Usage Examples

### Command-Line Interface

Generate embeddings with parallel processing:
```bash
python -m fooddb generate-embeddings --parallel 4 --timeout 1800
```

Test vector search directly:
```bash
python -m fooddb vector-search "high protein breakfast" --limit 5
```

### In Code

```python
from fooddb.embeddings import search_food_by_text

# Perform semantic search
results = search_food_by_text("foods high in vitamin c", limit=10)
for fdc_id, description, similarity in results:
    print(f"{description} - {similarity:.2f}")
```