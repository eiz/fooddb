import time
import logging
import click
from fooddb.import_data import import_all_data

# Default logging configuration - will be overridden in CLI
logging.basicConfig(
    level=logging.ERROR,  # Default to ERROR level unless --verbose is used
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


@click.group()
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging (INFO level)",
)
def cli(verbose):
    """FoodDB CLI for managing the food database and MCP server."""
    # Override the root logger level if verbose flag is set
    if verbose:
        logging.getLogger().setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.ERROR)


@cli.command()
@click.option(
    "--data-dir",
    default="./data",
    help="Directory containing CSV files to import",
    type=click.Path(exists=True),
)
@click.option(
    "--db-path",
    default="sqlite:///fooddb.sqlite",
    help="SQLite database path",
)
@click.option(
    "--nuke",
    is_flag=True,
    help="Nuke the database before importing (clear all data)",
)
@click.option(
    "--fast/--safe",
    default=True,
    help="Use fast direct import (default) or slower but safer ORM import",
)
@click.option(
    "--embeddings/--no-embeddings",
    default=True,
    help="Generate embeddings for vector search",
)
@click.option(
    "--parallel",
    default=1,
    type=int,
    help="Number of parallel API requests for embeddings (1 = sequential)",
)
@click.option(
    "--timeout",
    default=600,
    type=int,
    help="Maximum time for embedding generation in seconds (default: 10 minutes)",
)
def init_db(data_dir, db_path, nuke, fast, embeddings, parallel, timeout):
    """Initialize the database with USDA food data."""
    click.echo(f"Importing data from {data_dir} to {db_path}")
    click.echo(f"Using {'fast' if fast else 'safe'} import method")
    if nuke:
        click.echo("⚠️ Nuking database before import!")
    if embeddings:
        parallel_mode = "parallel" if parallel > 1 else "sequential"
        click.echo(f"Will generate embeddings after import in {parallel_mode} mode ({parallel} workers)")
        click.echo(f"Embedding generation will timeout after {timeout} seconds")
    
    start_time = time.time()
    import_all_data(
        data_dir, 
        db_path, 
        nuke=nuke, 
        fast=fast, 
        create_embeddings=embeddings, 
        parallel=parallel,
        timeout=timeout
    )
    elapsed_time = time.time() - start_time
    click.echo(f"Database initialization complete in {elapsed_time:.2f} seconds")


@cli.command()
@click.option(
    "--batch-size",
    default=1000,
    type=int,
    help="Number of foods to process in a batch",
)
@click.option(
    "--db-path",
    default="sqlite:///fooddb.sqlite",
    help="SQLite database path",
)
@click.option(
    "--parallel",
    default=1,
    type=int,
    help="Number of parallel API requests (1 = sequential)",
)
@click.option(
    "--timeout",
    default=600,
    type=int,
    help="Maximum execution time in seconds (default: 10 minutes)",
)
def generate_embeddings(batch_size, db_path, parallel, timeout):
    """Generate or update food embeddings for vector search."""
    from fooddb.embeddings import setup_vector_db, generate_batch_embeddings
    
    click.echo(f"Setting up vector database at {db_path}")
    setup_vector_db(db_path)
    
    parallel_mode = "parallel" if parallel > 1 else "sequential"
    click.echo(f"Generating embeddings in {parallel_mode} mode ({parallel} workers)")
    click.echo(f"Operation will timeout after {timeout} seconds")
    
    start_time = time.time()
    generate_batch_embeddings(
        batch_size=batch_size, 
        db_path=db_path, 
        parallel=parallel,
        timeout=timeout
    )
    
    elapsed_time = time.time() - start_time
    click.echo(f"Embedding generation complete in {elapsed_time:.2f} seconds")


@cli.command()
@click.option(
    "--transport",
    default="stdio",
    type=click.Choice(["stdio", "http"]),
    help="Transport protocol to use for MCP server",
)
@click.option(
    "--port",
    default=8000,
    type=int,
    help="Port to use when using HTTP transport",
)
def run_server(transport, port):
    """Run the MCP server using the specified transport."""
    # Import here to avoid circular imports
    from fooddb.server import mcp
    
    click.echo(f"Starting FoodDB MCP server with {transport} transport")
    
    if transport == "http":
        mcp.run(transport=transport, port=port)
    else:
        mcp.run(transport=transport)


@cli.command()
@click.argument("query")
@click.option(
    "--limit",
    default=10,
    type=int,
    help="Maximum number of results to return",
)
@click.option(
    "--db-path",
    default="sqlite:///fooddb.sqlite",
    help="SQLite database path",
)
@click.option(
    "--model",
    default="text-embedding-3-small",
    help="OpenAI embedding model to use",
)
def vector_search(query: str, limit: int, db_path: str, model: str):
    """
    Search for foods using semantic vector search.
    
    QUERY is the text to search for (e.g., "high protein breakfast").
    """
    from fooddb.embeddings import search_food_by_text
    
    click.echo(f"🔍 Searching for foods matching: '{query}'")
    click.echo(f"Using model: {model}")
    
    start_time = time.time()
    results = search_food_by_text(query, limit, model, db_path)
    elapsed_time = time.time() - start_time
    
    if not results:
        click.echo("No results found or OpenAI API key not set.")
        return
    
    click.echo(f"\nFound {len(results)} results in {elapsed_time:.2f} seconds:\n")
    
    # Display results in a table format
    click.echo(f"{'ID':<12} {'Similarity':<12} Description")
    click.echo("-" * 80)
    
    for fdc_id, description, similarity in results:
        # Format similarity as percentage
        similarity_pct = f"{similarity * 100:.1f}%"
        click.echo(f"{fdc_id:<12} {similarity_pct:<12} {description}")


if __name__ == "__main__":
    cli()