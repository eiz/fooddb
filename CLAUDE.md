# CLAUDE.md - FoodDB Project Guidelines

## Build/Run Commands
- `uv pip install -e .` - Install package in development mode
- `uv run python -m fooddb.server` - Run the MCP server
- `uv run pytest` - Run all tests
- `uv run pytest tests/test_specific.py::test_function` - Run specific test
- `uv run ruff check .` - Run linter

## Code Style Guidelines
- **Package Manager**: Use uv for dependency management
- **Formatting**: Black with default settings
- **Imports**: 
  - stdlib → third-party → local (sorted alphabetically)
  - All imports must be at the top module level, not inside functions
  - Only exception is for platform-specific imports needed for conditional logic
- **Types**: Type hints required for all functions and classes
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Error Handling**: Use specific exceptions with context
- **MCP Design**: Follow MCP protocol for request/response handling
- **Data Processing**: Use pandas for USDA data manipulation
- **API Design**: RESTful endpoints with consistent response format
- **Simplicity**: Only add optional parameters if explicitly requested. Keep code lean and mean.