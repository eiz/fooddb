from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fooddb.server import (
    FoodDBService,
    FoodInfo,
    Macros,
    ServingInfo,
    get_food_by_id,
    mcp,
    search_foods,
    search_foods_ai,
    semantic_food_search,
)


@pytest.fixture
def mock_food_service():
    """Create a mock food service."""
    # Create a mock service
    mock_service = MagicMock(spec=FoodDBService)
    
    # Setup mock food data
    test_macros = Macros(
        calories=100.0,
        protein=5.0,
        carbs=10.0,
        fat=2.0,
        fiber=1.0,
    )
    
    test_serving = ServingInfo(
        amount=1.0,
        unit="cup",
        grams=100.0,
        description="Test serving",
    )
    
    test_food = FoodInfo(
        id=12345,
        name="Test Food",
        category="Test Category",
        macros=test_macros,
        servings=[test_serving],
    )
    
    # Configure mock method responses
    mock_service.get_food_by_id = AsyncMock(return_value=test_food)
    mock_service.search_foods = AsyncMock(return_value=[test_food])
    mock_service.search_foods_ai = AsyncMock(return_value=[test_food])
    
    return mock_service


@pytest.mark.asyncio
async def test_get_food_by_id_tool(mock_food_service):
    """Test the get_food_by_id MCP tool."""
    with patch("fooddb.server.food_service", mock_food_service):
        # Call the MCP tool
        result = await get_food_by_id(12345)
        
        # Verify the service was called correctly
        mock_food_service.get_food_by_id.assert_called_once_with(12345)
        
        # Verify the result
        assert result is not None
        assert result["id"] == 12345
        assert result["name"] == "Test Food"
        assert result["category"] == "Test Category"
        
        # Check macros
        assert result["macros"]["calories"] == 100.0
        assert result["macros"]["protein"] == 5.0
        
        # Check servings
        assert len(result["servings"]) == 1
        assert result["servings"][0]["unit"] == "cup"
        assert result["servings"][0]["grams"] == 100.0


@pytest.mark.asyncio
async def test_search_foods_tool(mock_food_service):
    """Test the search_foods MCP tool."""
    with patch("fooddb.server.food_service", mock_food_service):
        # Call the MCP tool
        results = await search_foods("Test", 5)
        
        # Verify the service was called correctly
        mock_food_service.search_foods.assert_called_once_with("Test", 5)
        
        # Verify the results
        assert len(results) == 1
        assert results[0]["id"] == 12345
        assert results[0]["name"] == "Test Food"


@pytest.mark.asyncio
async def test_search_foods_ai_tool(mock_food_service):
    """Test the search_foods_ai MCP tool."""
    with patch("fooddb.server.food_service", mock_food_service):
        # Call the MCP tool
        results = await search_foods_ai("Test", 5)
        
        # Verify the service was called correctly
        mock_food_service.search_foods_ai.assert_called_once_with("Test", 5)
        
        # Verify the results
        assert len(results) == 1
        assert results[0]["id"] == 12345
        assert results[0]["name"] == "Test Food"


@pytest.mark.asyncio
async def test_semantic_food_search_tool():
    """Test the semantic_food_search MCP tool."""
    # Create mock vector search results
    vector_results = [(12345, "Test Food", 0.95)]
    
    # Mock the database session query
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_all = MagicMock(return_value=[
        MagicMock(fdc_id=12345, description="Test Food")
    ])
    mock_filter.all.return_value = mock_all.return_value
    mock_query.filter.return_value = mock_filter
    
    food_service_mock = MagicMock()
    food_service_mock.session.query.return_value = mock_query
    
    # Mock the food service's format method
    mock_food_info = FoodInfo(
        id=12345,
        name="Test Food",
        category="Test Category",
        macros=Macros(calories=100.0),
        servings=[]
    )
    food_service_mock._format_food_info.return_value = mock_food_info
    
    # Mock the embedding search function
    with patch("fooddb.server.search_food_by_text", return_value=vector_results), \
         patch("fooddb.server.food_service", food_service_mock):
        
        # Call the MCP tool
        results = await semantic_food_search("healthy breakfast", 5)
        
        # Verify the embedding search was called
        from fooddb.server import search_food_by_text
        search_food_by_text.assert_called_once_with("healthy breakfast", limit=5)
        
        # Verify the results
        assert len(results) == 1
        assert results[0]["id"] == 12345
        assert results[0]["name"] == "Test Food"


@pytest.mark.asyncio
async def test_mcp_tools_registration():
    """Test that the MCP tools are registered correctly."""
    # Get the tools from the MCP server
    tools = await mcp.list_tools()
    
    # Verify the tools
    tool_names = [tool.name for tool in tools]
    assert "search_foods" in tool_names
    assert "search_foods_ai" in tool_names
    assert "semantic_food_search" in tool_names
    assert "get_food_by_id" in tool_names