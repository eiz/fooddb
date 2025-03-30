# FoodDB - USDA Food Database MCP Server

An MCP server for querying USDA Food Data Central information. It provides tools to search for foods and get detailed nutritional information.

## Features

- Import USDA Food Data Central CSV files into a SQLite database
- Model Context Protocol (MCP) server for integration with Claude for Desktop and other MCP clients
- Smart keyword-based search for food items
- Semantic vector search using OpenAI embeddings
- Comprehensive nutritional data including calories, macros, and serving sizes

## Installation

```bash
# Install in development mode
uv pip install -e .
```

## Usage

### Initialize the Database

Before using the server, you need to import the USDA data:

```bash
# Import data from the default location (./data) with embeddings generation
uv run python -m fooddb.cli init-db

# Custom data and database paths
uv run python -m fooddb.cli init-db --data-dir /path/to/data --db-path sqlite:///custom.sqlite

# Skip embeddings generation
uv run python -m fooddb.cli init-db --no-embeddings
```

### Generate Embeddings

If you need to generate or update embeddings for vector search:

```bash
# Generate ALL embeddings for foods that don't have them yet
uv run python -m fooddb.cli generate-embeddings

# Process foods in larger batches (default is 1000)
uv run python -m fooddb.cli generate-embeddings --batch-size 5000
```

For vector search to work, you need to set the `OPENAI_API_KEY` environment variable:

```bash
export OPENAI_API_KEY=your-api-key
```

### Run the MCP Server

Run the server with the stdio transport (for use with Claude Desktop):

```bash
uv run python -m fooddb.cli run-server
```

Or with the HTTP transport for other clients:

```bash
uv run python -m fooddb.cli run-server --transport http --port 8000
```

## Integrating with Claude for Desktop

To use this server with Claude for Desktop, add it to your Claude Desktop configuration at `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "fooddb": {
            "command": "uv",
            "args": [
                "--directory",
                "/path/to/fooddb",
                "run",
                "python",
                "-m",
                "fooddb.cli",
                "run-server"
            ]
        }
    }
}
```

## MCP Tools

The server provides the following MCP tools:

### search_foods

Search for foods by name/description using basic text matching.

```python
search_foods(query: str, limit: int = 5) -> List[Dict]
```

### search_foods_ai

Search for foods using an enhanced matching algorithm, with vector search as a first option when available.

```python
search_foods_ai(query: str, limit: int = 5) -> List[Dict]
```

### semantic_food_search

Search for foods using AI vector embeddings for semantic matching. This can find foods that match the concept even if they don't contain the exact keywords.

```python
semantic_food_search(query: str, limit: int = 10) -> List[Dict]
```

### get_food_by_id

Get detailed information about a specific food by ID.

```python
get_food_by_id(food_id: int) -> Optional[Dict]
```

## Development

### Running Tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
```

## Data Structure

The USDA Food Data Central dataset includes:

- **Food**: Basic food information (name, category, etc.)
- **Nutrient**: Definitions of nutrients (calories, protein, etc.)
- **FoodNutrient**: Mapping of foods to their nutrient values
- **FoodPortion**: Serving size information for foods
- **FoodEmbeddings**: Vector embeddings for semantic search

## Vector Search

The system uses OpenAI's text-embedding-3-small model to generate vector embeddings for food descriptions. These embeddings are stored in the SQLite database using the sqlite-vec extension, which enables efficient similarity searches.

For vector search functionality:

1. Make sure the sqlite-vec extension is installed and available
2. Set the OPENAI_API_KEY environment variable
3. Generate embeddings during database initialization or with the generate-embeddings command
4. Use the semantic_food_search MCP tool for natural language food searches