# MCP Server Implementation

This document explains the Model Context Protocol (MCP) server implementation in FoodDB.

## Overview

FoodDB includes an MCP server that allows Claude and other AI assistants to access food and nutrition data through a structured API. The server implements tools for searching foods and retrieving detailed nutritional information.

## MCP Protocol

The Model Context Protocol (MCP) allows AI assistants to interact with external systems through well-defined tools. FoodDB implements an MCP server that supports both stdio and HTTP transports:

- **stdio transport**: Used with Claude for Desktop and similar clients
- **HTTP transport**: Used for web-based or custom integrations

## Server Implementation

The MCP server is implemented in `fooddb/server.py` and exposes several tools:

### Tool: search_foods

```python
def search_foods(query: str, limit: int = 5) -> List[Dict]:
    """
    Search for foods by name/description using basic text matching.
    
    Args:
        query: Text to search for
        limit: Maximum number of results to return
        
    Returns:
        List of food dictionaries with basic information
    """
```

This tool uses basic SQL LIKE queries to find foods with names/descriptions matching the query.

### Tool: search_foods_ai

```python
def search_foods_ai(query: str, limit: int = 5) -> List[Dict]:
    """
    Search for foods using an enhanced matching algorithm.
    
    If vector embeddings are available, this will use semantic search first,
    then fall back to keyword search.
    
    Args:
        query: Text to search for
        limit: Maximum number of results to return
        
    Returns:
        List of food dictionaries with basic information
    """
```

This tool tries vector search first (when available) and falls back to keyword search when vector search is unavailable or returns insufficient results.

### Tool: semantic_food_search

```python
def semantic_food_search(query: str, limit: int = 10) -> List[Dict]:
    """
    Search for foods using AI vector embeddings for semantic matching.
    
    This can find foods that match the concept even if they don't contain
    the exact keywords.
    
    Args:
        query: Text to search for
        limit: Maximum number of results to return
        
    Returns:
        List of food dictionaries with similarity scores
    """
```

This tool performs a pure vector similarity search without any keyword fallback.

### Tool: get_food_by_id

```python
def get_food_by_id(food_id: int) -> Optional[Dict]:
    """
    Get detailed information about a specific food by ID.
    
    Args:
        food_id: FDC ID of the food to retrieve
        
    Returns:
        Dictionary with comprehensive food information including nutrients
        and portions, or None if not found
    """
```

This tool retrieves detailed information about a specific food, including all nutrients and portion sizes.

## Running the Server

The server can be started using the CLI command:

```bash
python -m fooddb run-server [--transport http] [--port 8000]
```

## Integrating with Claude for Desktop

To use FoodDB with Claude for Desktop, add it to your Claude Desktop configuration at `~/Library/Application Support/Claude/claude_desktop_config.json`:

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
                "fooddb",
                "run-server"
            ]
        }
    }
}
```

## Example Interactions

When the MCP server is integrated with Claude, you can use commands like:

```
Can you help me find foods high in protein?
```

Claude will use the appropriate tools to search the database and return relevant results.

For more specific requests:

```
What nutrients are in salmon? Please search for it and give me details.
```

Claude will use search_foods or search_foods_ai to find salmon, then use get_food_by_id to retrieve detailed nutrient information.

## Implementation Details

### Database Connection

The server maintains a connection to the SQLite database and provides functions to convert database records to the JSON structures expected by the MCP protocol.

### Error Handling

The server includes error handling to gracefully handle cases such as:
- Invalid queries
- Missing OpenAI API key for vector search
- Database connection issues
- Missing database tables

### Response Formatting

All responses are formatted as JSON-serializable dictionaries or lists, following the MCP protocol specifications. Food records include:
- Basic information (ID, description, category)
- Nutrient information (when requested with get_food_by_id)
- Portion/serving size information
- Similarity scores (for vector search results)