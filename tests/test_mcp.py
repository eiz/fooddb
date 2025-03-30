from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fooddb.server import (
    FoodDBService,
    FoodSearchResult,
    mcp,
    food_search
)


@pytest.fixture
def mock_food_service():
    """Create a mock food service."""
    # Create a mock service
    mock_service = MagicMock(spec=FoodDBService)
    
    # Setup mock food search result
    test_result = FoodSearchResult(
        id=12345,
        name="Test Food",
        similarity=0.95
    )
    
    # Configure mock method responses
    mock_service.food_search = AsyncMock(return_value=[test_result])
    
    return mock_service


@pytest.mark.asyncio
async def test_food_search_tool(mock_food_service):
    """Test the food_search MCP tool."""
    with patch("fooddb.server.food_service", mock_food_service):
        # Call the MCP tool
        results = await food_search("Test", 5)
        
        # Verify the service was called correctly
        mock_food_service.food_search.assert_called_once_with("Test", 5, "text-embedding-3-small")
        
        # Verify the results
        assert len(results) == 1
        assert results[0]["id"] == 12345
        assert results[0]["name"] == "Test Food"
        assert results[0]["similarity"] == 0.95


@pytest.mark.asyncio
async def test_mcp_tools_registration():
    """Test that the MCP tools are registered correctly."""
    # Get the tools from the MCP server
    tools = await mcp.list_tools()
    
    # Verify the tools
    tool_names = [tool.name for tool in tools]
    assert "food_search" in tool_names