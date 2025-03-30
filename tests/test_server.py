from unittest.mock import MagicMock, patch

import pytest

from fooddb.models import (
    Food,
    FoodNutrient,
    FoodPortion,
    Nutrient,
    BrandedFood,
)
from fooddb.server import FoodDBService


@pytest.fixture
def mock_session():
    """Create a mock database session with test data."""
    # Create a mock session
    mock_session = MagicMock()
    
    # Setup some test data
    test_food = Food(
        fdc_id=12345,
        data_type="test",
        description="Test Food",
        food_category_id="Test Category",
    )
    
    test_nutrient_calories = Nutrient(
        id=1008,
        name="Energy",
        unit_name="KCAL",
        nutrient_nbr="208",
    )
    
    test_nutrient_protein = Nutrient(
        id=1003,
        name="Protein",
        unit_name="G",
        nutrient_nbr="203",
    )
    
    test_food_nutrient_calories = FoodNutrient(
        id=10001,
        fdc_id=12345,
        nutrient_id=1008,
        amount=200.0,
        nutrient=test_nutrient_calories,
    )
    
    test_food_nutrient_protein = FoodNutrient(
        id=10002,
        fdc_id=12345,
        nutrient_id=1003,
        amount=10.0,
        nutrient=test_nutrient_protein,
    )
    
    test_food_portion = FoodPortion(
        id=20001,
        fdc_id=12345,
        seq_num=1,
        amount=1.0,
        measure_unit_id="serving",
        portion_description="Test portion",
        modifier="cup",
        gram_weight=100.0,
    )
    
    # Create test branded food with proper string attributes for Pydantic validation
    test_branded_food = MagicMock()
    test_branded_food.fdc_id = 12345
    test_branded_food.brand_owner = "Test Brand Owner"
    test_branded_food.brand_name = "Test Brand"
    test_branded_food.ingredients = "Test Ingredients"
    test_branded_food.serving_size = 100.0
    test_branded_food.serving_size_unit = "g"
    test_branded_food.household_serving_fulltext = "1 cup"
    test_branded_food.branded_food_category = "Test Category"
    
    # Configure mock query responses
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    
    # Configure filter for Food query
    mock_food_filter = MagicMock()
    mock_food_filter.first.return_value = test_food
    mock_food_filter.all.return_value = [test_food]
    mock_food_filter.limit.return_value = mock_food_filter
    
    # Configure filter for FoodNutrient query
    mock_nutrients_filter = MagicMock()
    mock_nutrients_options = MagicMock()
    mock_nutrients_options.all.return_value = [
        test_food_nutrient_calories, 
        test_food_nutrient_protein
    ]
    mock_nutrients_filter.options.return_value = mock_nutrients_options
    
    # Configure filter for FoodPortion query
    mock_portions_filter = MagicMock()
    mock_portions_filter.all.return_value = [test_food_portion]
    
    # Configure filter for BrandedFood query
    mock_branded_filter = MagicMock()
    mock_branded_filter.first.return_value = test_branded_food
    
    # Configure query behavior based on queried model
    def query_side_effect(model):
        if model == Food:
            mock_query.filter.return_value = mock_food_filter
            mock_query.filter_by.return_value = mock_food_filter
            return mock_query
        elif model == FoodNutrient:
            mock_query.filter.return_value = mock_nutrients_filter
            return mock_query
        elif model == FoodPortion:
            mock_query.filter.return_value = mock_portions_filter
            return mock_query
        elif model == BrandedFood:
            mock_query.filter.return_value = mock_branded_filter
            return mock_query
        return mock_query
    
    mock_session.query.side_effect = query_side_effect
    
    return mock_session


@pytest.mark.asyncio
async def test_get_food_by_id(mock_session):
    """Test retrieving food details by ID."""
    with patch("fooddb.server.get_db_session", return_value=(mock_session, None)):
        food_service = FoodDBService()
        
        # Get food by ID
        food_info = await food_service.get_food_by_id(12345)
        
        # Verify the result
        assert food_info is not None
        assert food_info.id == 12345
        assert food_info.name == "Test Food"
        assert food_info.category == "Test Category"
        
        # Check macros
        assert food_info.macros.calories == 200.0
        assert food_info.macros.protein == 10.0
        
        # Check servings
        assert len(food_info.servings) == 1
        assert food_info.servings[0].unit == "cup"
        assert food_info.servings[0].grams == 100.0


@pytest.mark.asyncio
async def test_search_foods(mock_session):
    """Test searching for foods by name."""
    with patch("fooddb.server.get_db_session", return_value=(mock_session, None)):
        food_service = FoodDBService()
        
        # Search for foods
        results = await food_service.search_foods("Test")
        
        # Verify the results
        assert len(results) == 1
        assert results[0].id == 12345
        assert results[0].name == "Test Food"


@pytest.mark.asyncio
async def test_search_foods_ai(mock_session):
    """Test searching for foods using AI."""
    with patch("fooddb.server.get_db_session", return_value=(mock_session, None)):
        food_service = FoodDBService()
        
        # Search for foods using AI
        results = await food_service.search_foods_ai("Test")
        
        # Verify the results
        assert len(results) == 1
        assert results[0].id == 12345
        assert results[0].name == "Test Food"