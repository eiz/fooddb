# MCP Server Implementation

This document explains the Model Context Protocol (MCP) server implementation in FoodDB.

## Overview

FoodDB includes an MCP server that allows Claude and other AI assistants to access food and nutrition data through a structured API. The server implements a streamlined semantic food search tool to help find foods using natural language queries.

## MCP Protocol

The Model Context Protocol (MCP) allows AI assistants to interact with external systems through well-defined tools. FoodDB implements an MCP server that supports both stdio and HTTP transports:

- **stdio transport**: Used with Claude for Desktop and similar clients
- **HTTP transport**: Used for web-based or custom integrations

## Server Implementation

The MCP server is implemented in `fooddb/server.py` and exposes a single tool:

### Tool: food_search

```python
def food_search(query: str, limit: int = 10, model: str = "text-embedding-3-small") -> List[Dict]:
    """
    Search for foods using semantic vector search.
    
    This search uses AI embeddings to find foods that semantically match your query,
    even if they don't contain the exact words. For example, searching for
    "high protein breakfast" might return results like "egg" or "Greek yogurt".
    
    Args:
        query: Text to search for (e.g., "high protein breakfast", "vegan dessert")
        limit: Maximum number of results to return (default: 10)
        model: OpenAI embedding model to use (default: "text-embedding-3-small")
    
    Returns:
        List of food items with similarity scores
    """
```

This tool uses OpenAI embeddings to perform semantic vector search, finding foods that conceptually match the query even if they don't contain the exact keywords. The results include:

- Food ID (FDC ID)
- Food name/description
- Similarity score (0-1 scale, where 1 is exact match)

## Running the Server

The server can be started using the CLI command:

```bash
# Using the module
python -m fooddb run-server [--transport http] [--port 8000]

# Using the binary
food run-server [--transport http] [--port 8000]
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
                "food",
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

Claude will use the `food_search` tool to search the database and return relevant results.

For more specific requests:

```
What are some healthy breakfast options? Can you search for breakfast foods?
```

Claude will use the `food_search` tool with a query like "healthy breakfast" to retrieve semantic matches.

## Implementation Details

### Database Connection

The server maintains a connection to the SQLite database and uses the same vector search implementation as the CLI command.

### Vector Search

The semantic search uses:
- OpenAI embeddings for query vectors
- sqlite-vec extension for efficient KNN similarity search
- Pydantic models for clean API response formatting

### Error Handling

The server includes error handling to gracefully handle cases such as:
- Invalid queries
- Missing OpenAI API key for vector search
- Database connection issues

### Response Format

The response format is simplified to focus on the most important information:

```json
[
  {
    "id": 167566,
    "name": "Egg, whole, raw, fresh",
    "similarity": 0.954
  },
  {
    "id": 171287,
    "name": "Egg, whole, cooked, omelet",
    "similarity": 0.942
  },
  ...
]
```