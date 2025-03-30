# FoodDB Architecture

This document describes the architecture and implementation details of the FoodDB project.

## Project Structure

The project is organized into the following modules:

### `fooddb/__init__.py`
- Package initialization

### `fooddb/__main__.py`
- Entry point for the CLI command interface

### `fooddb/cli.py`
- CLI command definitions using Click
- Commands: init-db, generate-embeddings, vector-search, run-server

### `fooddb/models.py`
- SQLAlchemy ORM models for USDA food data
- Tables: Food, Nutrient, FoodNutrient, FoodPortion
- Database connection and initialization functions

### `fooddb/import_data.py`
- Functions to import USDA CSV data into the database
- CSV parsing and bulk database insertions
- Integration with embedding generation

### `fooddb/embeddings.py`
- Vector embedding generation using OpenAI API
- Parallel processing support for faster embedding generation
- Vector search functionality using sqlite-vec
- SQL query logging for performance monitoring
- Timeout support to limit execution time

### `fooddb/server.py`
- MCP server implementation
- Tool definitions for interacting with the food database
- Integration with vector search for AI-powered queries

## Data Model

The USDA Food Data Central dataset is represented using the following tables:

- **Food**: Basic food information (name, category, etc.)
- **Nutrient**: Definitions of nutrients (calories, protein, etc.)
- **FoodNutrient**: Mapping of foods to their nutrient values
- **FoodPortion**: Serving size information for foods
- **FoodEmbeddings**: Vector embeddings for semantic search

## Database Schema

### Food Table
- `fdc_id` (PK): Integer food identifier
- `data_type`: Type of food (e.g., branded, survey, etc.)
- `description`: Food name/description
- `food_category_id`: Category identifier
- `publication_date`: Date the food data was published

### Nutrient Table
- `id` (PK): Integer nutrient identifier
- `name`: Nutrient name (e.g., "Protein")
- `unit_name`: Unit of measurement (e.g., "g")
- `nutrient_nbr`: USDA nutrient number
- `rank`: Display order priority

### FoodNutrient Table
- `id` (PK): Row identifier
- `fdc_id` (FK): Reference to Food
- `nutrient_id` (FK): Reference to Nutrient
- `amount`: Nutrient value

### FoodPortion Table
- `id` (PK): Row identifier
- `fdc_id` (FK): Reference to Food
- `seq_num`: Sequence number for ordering
- `amount`: Portion amount
- `measure_unit_id`: Unit identifier
- `portion_description`: Description of the portion
- `modifier`: Additional description (e.g., "cup")
- `gram_weight`: Weight in grams

### FoodEmbeddings Table
- `fdc_id` (PK): Reference to Food
- `embedding`: BLOB of vector data
- `embedding_model`: Model used to generate the embedding