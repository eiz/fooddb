# CLI Interface Documentation

This document describes the command-line interface (CLI) for the FoodDB project.

## Overview

FoodDB provides a comprehensive command-line interface built using the Click framework. The CLI enables users to initialize the database, generate embeddings, test vector search, and run the MCP server.

## Installation

To use the CLI, install the package in development mode:

```bash
uv pip install -e .
```

After installation, you can use either:
- The module approach: `python -m fooddb [COMMAND]`
- The `food` command directly: `food [COMMAND]`

The `food` command is available in your environment's bin directory and should be automatically in your PATH when your virtual environment is active.

## Commands

### init-db

Initializes the database with USDA food data.

```bash
python -m fooddb init-db [OPTIONS]
```

Options:
* `--data-dir PATH`: Directory containing CSV files to import (default: ./data)
* `--db-path TEXT`: SQLite database path (default: sqlite:///fooddb.sqlite)
* `--nuke`: Nuke the database before importing (clear all data)
* `--fast/--safe`: Use fast direct import (default) or slower but safer ORM import
* `--embeddings/--no-embeddings`: Generate embeddings for vector search (default: True)
* `--parallel INTEGER`: Number of parallel API requests for embeddings (default: 1)
* `--timeout INTEGER`: Maximum time for embedding generation in seconds (default: 600)

Examples:
```bash
# Basic usage with defaults
python -m fooddb init-db

# Custom data directory, nuke existing data
python -m fooddb init-db --data-dir /path/to/data --nuke

# Skip embedding generation
python -m fooddb init-db --no-embeddings

# Use parallel embedding generation with 4 workers
python -m fooddb init-db --parallel 4
```

### generate-embeddings

Generates or updates food embeddings for vector search.

```bash
python -m fooddb generate-embeddings [OPTIONS]
```

Options:
* `--batch-size INTEGER`: Number of foods to process in a batch (default: 1000)
* `--db-path TEXT`: SQLite database path (default: sqlite:///fooddb.sqlite)
* `--parallel INTEGER`: Number of parallel API requests (default: 1)
* `--timeout INTEGER`: Maximum execution time in seconds (default: 600)

Examples:
```bash
# Basic usage with defaults
python -m fooddb generate-embeddings

# Generate embeddings in larger batches
python -m fooddb generate-embeddings --batch-size 5000

# Use parallel processing with 8 workers
python -m fooddb generate-embeddings --parallel 8

# Set a longer timeout for large datasets
python -m fooddb generate-embeddings --timeout 1800
```

### search

Searches for foods using semantic vector search.

```bash
python -m fooddb search QUERY... [OPTIONS]
# Or using the 'food' command:
food search QUERY... [OPTIONS]
```

Arguments:
* `QUERY...`: The text to search for. Multiple words are combined into a single query (e.g., high protein breakfast)

Options:
* `--limit INTEGER`: Maximum number of results to return (default: 10)
* `--db-path TEXT`: SQLite database path (default: sqlite:///fooddb.sqlite)
* `--model TEXT`: OpenAI embedding model to use (default: text-embedding-3-small)

Examples:
```bash
# Basic search - no quotes needed around multi-word queries
python -m fooddb search high protein breakfast
food search high protein breakfast

# Limit results to 5 items
python -m fooddb search vegetarian dinner --limit 5
food search vegetarian dinner --limit 5

# Use a different model
python -m fooddb search foods for athletes --model text-embedding-3-large
food search foods for athletes --model text-embedding-3-large
```

Output format:
```
ID           Similarity   Description
----------------------------------------------------------------
167566       95.4%        Egg, whole, raw, fresh
171287       94.2%        Egg, whole, cooked, omelet
168997       93.8%        Greek yogurt, plain, whole milk
```

### run-server

Runs the MCP server using the specified transport.

```bash
python -m fooddb run-server [OPTIONS]
```

Options:
* `--transport [stdio|http]`: Transport protocol to use for MCP server (default: stdio)
* `--port INTEGER`: Port to use when using HTTP transport (default: 8000)

Examples:
```bash
# Run with stdio transport (for Claude Desktop)
python -m fooddb run-server

# Run with HTTP transport on port 8080
python -m fooddb run-server --transport http --port 8080
```

## Implementation

The CLI is implemented in `fooddb/cli.py` using the Click framework. The commands are defined using Click decorators and are organized in a command group.

Each command imports the necessary functions from the appropriate modules to implement its functionality. For example, `init-db` uses functions from `import_data.py`, while `search` uses functions from `embeddings.py`.

### Entry Points

The CLI can be invoked in two ways:

1. Using the module:
```bash
python -m fooddb [COMMAND] [OPTIONS]
```

This works because of the entry point defined in `__main__.py` which imports and calls the CLI group function.

2. Using the `food` command:
```bash
food [COMMAND] [OPTIONS]
```

This works because of the console script entry point defined in `pyproject.toml`, which makes the `food` command available in your environment's bin directory.

## Error Handling

The CLI includes error handling for common issues:

* Missing data directory
* Database connection errors
* Missing OpenAI API key for embedding operations
* Timeouts during long-running operations

## Environment Variables

Some functionality depends on environment variables:

* `OPENAI_API_KEY`: Required for embedding generation and vector search