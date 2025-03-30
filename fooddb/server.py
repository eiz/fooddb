from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import joinedload

# Import the MCP server package
from mcp.server.fastmcp import FastMCP

from fooddb.models import (
    Food, 
    FoodNutrient, 
    FoodPortion, 
    Nutrient, 
    BrandedFood,
    FoodComponent,
    InputFood,
    get_db_session
)
from fooddb.embeddings import search_food_by_text

# Type definitions for our API responses
class Macros(BaseModel):
    calories: Optional[float] = Field(None, description="Calories in kcal")
    protein: Optional[float] = Field(None, description="Protein in grams")
    carbs: Optional[float] = Field(None, description="Carbohydrates in grams")
    fat: Optional[float] = Field(None, description="Total fat in grams")
    fiber: Optional[float] = Field(None, description="Dietary fiber in grams")


class ServingInfo(BaseModel):
    amount: float = Field(..., description="Amount of the serving")
    unit: str = Field(..., description="Unit of the serving (e.g., cup, tbsp)")
    grams: float = Field(..., description="Weight in grams")
    description: Optional[str] = Field(None, description="Description of the serving")


class ComponentInfo(BaseModel):
    name: str = Field(..., description="Component name")
    percent_weight: Optional[float] = Field(None, description="Percentage by weight")
    gram_weight: Optional[float] = Field(None, description="Weight in grams")
    is_refuse: Optional[bool] = Field(None, description="Whether this component is refuse/waste")


class IngredientInfo(BaseModel):
    seq_num: int = Field(..., description="Sequence number in recipe")
    amount: float = Field(..., description="Amount of ingredient")
    description: str = Field(..., description="Description of ingredient")
    unit: str = Field(..., description="Unit of measurement")
    gram_weight: float = Field(..., description="Weight in grams")


class BrandedFoodInfo(BaseModel):
    brand_owner: Optional[str] = Field(None, description="Brand owner name")
    brand_name: Optional[str] = Field(None, description="Brand name")
    ingredients: Optional[str] = Field(None, description="Ingredient list as text")
    serving_size: Optional[float] = Field(None, description="Serving size")
    serving_size_unit: Optional[str] = Field(None, description="Serving size unit")
    household_serving_fulltext: Optional[str] = Field(None, description="Household serving description")
    branded_food_category: Optional[str] = Field(None, description="Food category")


class FoodInfo(BaseModel):
    id: int = Field(..., description="Food ID")
    name: str = Field(..., description="Food name/description")
    category: Optional[str] = Field(None, description="Food category")
    macros: Macros = Field(..., description="Macronutrient information")
    servings: List[ServingInfo] = Field(default_factory=list, description="Available serving sizes")
    branded_food: Optional[BrandedFoodInfo] = Field(None, description="Branded food information if available")
    components: List[ComponentInfo] = Field(default_factory=list, description="Food components")
    ingredients: List[IngredientInfo] = Field(default_factory=list, description="Food ingredients")


# Nutrient IDs for macros (based on USDA FoodData Central)
NUTRIENT_IDS = {
    "calories": [1008, 2047, 2048],  # Energy in different calculation methods
    "protein": [1003, 1079, 1090],   # Protein
    "carbs": [1005, 1072, 1082],     # Carbohydrates
    "fat": [1004, 1293],             # Total fat
    "fiber": [1079, 1081, 1082, 1083, 1084, 1085]  # Dietary fiber
}


# Initialize MCP server
mcp = FastMCP("fooddb", description="USDA Food Database API for nutritional information")


class FoodDBService:
    def __init__(self):
        # Initialize database connection
        self.session, _ = get_db_session()
        
    def _get_macros_for_food(self, food_id: int) -> Macros:
        """Extract macro nutrients for a specific food."""
        # Query all nutrient data for this food
        nutrients = (
            self.session.query(FoodNutrient)
            .filter(FoodNutrient.fdc_id == food_id)
            .options(joinedload(FoodNutrient.nutrient))
            .all()
        )
        
        # Initialize macros with None values
        macros = Macros()
        
        # Process each nutrient
        for nutrient in nutrients:
            if not nutrient.amount:
                continue
                
            nutrient_id = nutrient.nutrient_id
            
            # Match nutrient to macro category
            if nutrient_id in NUTRIENT_IDS["calories"] and not macros.calories:
                macros.calories = nutrient.amount
            elif nutrient_id in NUTRIENT_IDS["protein"] and not macros.protein:
                macros.protein = nutrient.amount
            elif nutrient_id in NUTRIENT_IDS["carbs"] and not macros.carbs:
                macros.carbs = nutrient.amount
            elif nutrient_id in NUTRIENT_IDS["fat"] and not macros.fat:
                macros.fat = nutrient.amount
            elif nutrient_id in NUTRIENT_IDS["fiber"] and not macros.fiber:
                macros.fiber = nutrient.amount
        
        return macros
    
    def _get_servings_for_food(self, food_id: int) -> List[ServingInfo]:
        """Get serving information for a specific food."""
        # Query all portion data for this food
        portions = (
            self.session.query(FoodPortion)
            .filter(FoodPortion.fdc_id == food_id)
            .all()
        )
        
        servings = []
        for portion in portions:
            if not portion.gram_weight:
                continue
                
            # Extract meaningful unit and description
            unit = "serving"
            if portion.modifier:
                unit = portion.modifier
                
            description = portion.portion_description or ""
            
            serving = ServingInfo(
                amount=portion.amount or 1.0,
                unit=unit,
                grams=portion.gram_weight,
                description=description
            )
            servings.append(serving)
        
        # Add a default "100g" serving if no servings are available
        if not servings:
            servings.append(
                ServingInfo(
                    amount=100.0,
                    unit="g",
                    grams=100.0,
                    description="Standard 100g portion"
                )
            )
            
        return servings
    
    def _get_branded_food_info(self, food_id: int) -> Optional[BrandedFoodInfo]:
        """Get branded food information if available."""
        branded_food = (
            self.session.query(BrandedFood)
            .filter(BrandedFood.fdc_id == food_id)
            .first()
        )
        
        if not branded_food:
            return None
        
        return BrandedFoodInfo(
            brand_owner=branded_food.brand_owner,
            brand_name=branded_food.brand_name,
            ingredients=branded_food.ingredients,
            serving_size=branded_food.serving_size,
            serving_size_unit=branded_food.serving_size_unit,
            household_serving_fulltext=branded_food.household_serving_fulltext,
            branded_food_category=branded_food.branded_food_category
        )
    
    def _get_components_for_food(self, food_id: int) -> List[ComponentInfo]:
        """Get component information for a specific food."""
        components = (
            self.session.query(FoodComponent)
            .filter(FoodComponent.fdc_id == food_id)
            .all()
        )
        
        result = []
        for component in components:
            if not component.name:
                continue
                
            comp_info = ComponentInfo(
                name=component.name,
                percent_weight=component.pct_weight,
                gram_weight=component.gram_weight,
                is_refuse=component.is_refuse
            )
            result.append(comp_info)
            
        return result
    
    def _get_ingredients_for_food(self, food_id: int) -> List[IngredientInfo]:
        """Get ingredient information for a specific food."""
        ingredients = (
            self.session.query(InputFood)
            .filter(InputFood.fdc_id == food_id)
            .order_by(InputFood.seq_num)
            .all()
        )
        
        result = []
        for ingredient in ingredients:
            if not ingredient.sr_description:
                continue
                
            ing_info = IngredientInfo(
                seq_num=ingredient.seq_num or 0,
                amount=ingredient.amount or 0.0,
                description=ingredient.sr_description,
                unit=ingredient.unit or "g",
                gram_weight=ingredient.gram_weight or 0.0
            )
            result.append(ing_info)
            
        return result
        
    def _format_food_info(self, food: Food) -> FoodInfo:
        """Format a food record into a FoodInfo response."""
        macros = self._get_macros_for_food(food.fdc_id)
        servings = self._get_servings_for_food(food.fdc_id)
        branded_food = self._get_branded_food_info(food.fdc_id)
        components = self._get_components_for_food(food.fdc_id)
        ingredients = self._get_ingredients_for_food(food.fdc_id)
        
        return FoodInfo(
            id=food.fdc_id,
            name=food.description,
            category=food.food_category_id,
            macros=macros,
            servings=servings,
            branded_food=branded_food,
            components=components,
            ingredients=ingredients
        )

    async def search_foods(self, query: str, limit: int = 5) -> List[FoodInfo]:
        """
        Search for foods by description using a simple text match.
        
        Args:
            query: The search term
            limit: Maximum number of results to return
            
        Returns:
            List of matching food information
        """
        # Simple text search for now
        foods = (
            self.session.query(Food)
            .filter(Food.description.ilike(f"%{query}%"))
            .limit(limit)
            .all()
        )
        
        results = [self._format_food_info(food) for food in foods]
        return results
    
    async def search_foods_ai(self, query: str, limit: int = 5) -> List[FoodInfo]:
        """
        Search for foods using AI to improve matching.
        
        Args:
            query: The search term
            limit: Maximum number of results to return
            
        Returns:
            List of matching food information
        """
        # First try vector search if available
        try:
            # Get semantic search results using embeddings
            vector_results = search_food_by_text(query, limit=limit)
            
            if vector_results:
                # If vector search worked, get the food objects and format them
                food_ids = [result[0] for result in vector_results]
                foods = self.session.query(Food).filter(Food.fdc_id.in_(food_ids)).all()
                
                # Order the foods to match the order of the vector search results
                food_map = {food.fdc_id: food for food in foods}
                ordered_foods = [food_map[fdc_id] for fdc_id in food_ids if fdc_id in food_map]
                
                # Format and return results
                results = [self._format_food_info(food) for food in ordered_foods]
                return results
        except Exception as e:
            print(f"Vector search failed, falling back to text search: {e}")
        
        # Fallback to advanced text search
        sample_size = 1000  # Adjust based on your needs
        
        # Get a random sample of foods
        sample_foods = (
            self.session.query(Food)
            .order_by(func.random())
            .limit(sample_size)
            .all()
        )
        
        # Create a simple relevance scoring system
        # Higher score = better match
        scored_foods = []
        for food in sample_foods:
            score = 0
            
            # Full match in description
            if query.lower() in food.description.lower():
                score += 10
                
            # Words match (partial)
            query_words = set(query.lower().split())
            desc_words = set(food.description.lower().split())
            
            common_words = query_words.intersection(desc_words)
            score += len(common_words) * 5
            
            # Add if has any score
            if score > 0:
                scored_foods.append((food, score))
        
        # Sort by score (descending) and take top results
        scored_foods.sort(key=lambda x: x[1], reverse=True)
        top_foods = [food for food, _ in scored_foods[:limit]]
        
        # If we don't have enough matches, fall back to the regular search
        if len(top_foods) < limit:
            # Use the standard search as fallback
            fallback_foods = (
                self.session.query(Food)
                .filter(Food.description.ilike(f"%{query}%"))
                .limit(limit - len(top_foods))
                .all()
            )
            
            # Append unique fallback foods
            existing_ids = {food.fdc_id for food in top_foods}
            for food in fallback_foods:
                if food.fdc_id not in existing_ids:
                    top_foods.append(food)
                    existing_ids.add(food.fdc_id)
                    
                    # Stop if we've reached the limit
                    if len(top_foods) >= limit:
                        break
        
        # Format and return results
        results = [self._format_food_info(food) for food in top_foods]
        return results
    
    async def get_food_by_id(self, food_id: int) -> Optional[FoodInfo]:
        """
        Get detailed information about a specific food by ID.
        
        Args:
            food_id: The FDC ID of the food
            
        Returns:
            Food information or None if not found
        """
        food = self.session.query(Food).filter(Food.fdc_id == food_id).first()
        
        if not food:
            return None
            
        return self._format_food_info(food)


# Initialize the service
food_service = FoodDBService()


# Register MCP tools
@mcp.tool()
async def search_foods(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search for foods by name/description.
    
    Args:
        query: The search term to look for in food descriptions
        limit: Maximum number of results to return
    """
    results = await food_service.search_foods(query, limit)
    # Convert Pydantic models to dictionaries for MCP compatibility
    return [result.model_dump() for result in results]


@mcp.tool()
async def search_foods_ai(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search for foods using AI for better matching.
    
    Args:
        query: The search term or description of what you're looking for
        limit: Maximum number of results to return
    """
    results = await food_service.search_foods_ai(query, limit)
    # Convert Pydantic models to dictionaries for MCP compatibility
    return [result.model_dump() for result in results]


@mcp.tool()
async def semantic_food_search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for foods using vector embeddings for semantic matching.
    
    This search tool uses AI embeddings to find foods that semantically match
    your query, even if they don't contain the exact words. For example, searching
    for "breakfast cereal" might return results like "corn flakes" or "granola".
    
    Args:
        query: Natural language description of the food you're looking for
        limit: Maximum number of results to return
    """
    # First try using vector search
    try:
        # Get semantic search results using embeddings
        vector_results = search_food_by_text(query, limit=limit)
        
        if vector_results:
            # If vector search worked, get the food objects
            food_ids = [result[0] for result in vector_results]
            foods = food_service.session.query(Food).filter(Food.fdc_id.in_(food_ids)).all()
            
            # Order the foods to match the order of the vector search results
            food_map = {food.fdc_id: food for food in foods}
            ordered_foods = [food_map[fdc_id] for fdc_id in food_ids if fdc_id in food_map]
            
            # Format results
            food_results = [food_service._format_food_info(food) for food in ordered_foods]
            return [result.model_dump() for result in food_results]
    except Exception as e:
        print(f"Vector search failed: {e}")
        return []
    
    # If we couldn't get results via vector search, return empty list
    return []


@mcp.tool()
async def get_food_by_id(food_id: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific food by ID.
    
    Args:
        food_id: The FDC ID of the food
    """
    result = await food_service.get_food_by_id(food_id)
    # Convert Pydantic model to dictionary for MCP compatibility
    return result.model_dump() if result else None


@mcp.tool()
async def search_foods_by_ingredient(ingredient: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search for foods containing a specific ingredient.
    
    This search looks for the ingredient in branded food ingredient lists
    and in the input foods that make up composite foods.
    
    Args:
        ingredient: Ingredient name to search for
        limit: Maximum number of results to return
    """
    # Search in branded foods' ingredients lists
    branded_foods = (
        food_service.session.query(BrandedFood)
        .filter(BrandedFood.ingredients.ilike(f"%{ingredient}%"))
        .limit(limit * 2)  # Get more than needed since some might be filtered out
        .all()
    )
    
    food_ids = []
    for bf in branded_foods:
        if len(food_ids) >= limit:
            break
        food_ids.append(bf.fdc_id)
    
    # Get the ingredients from input foods
    input_foods = (
        food_service.session.query(InputFood)
        .filter(InputFood.sr_description.ilike(f"%{ingredient}%"))
        .limit(limit * 2)
        .all()
    )
    
    for input_food in input_foods:
        if len(food_ids) >= limit:
            break
        if input_food.fdc_id not in food_ids:
            food_ids.append(input_food.fdc_id)
    
    # Get the food objects
    foods = food_service.session.query(Food).filter(Food.fdc_id.in_(food_ids)).all()
    
    # Format results
    results = [food_service._format_food_info(food) for food in foods]
    return [result.model_dump() for result in results[:limit]]


@mcp.tool()
async def get_ingredient_info(ingredient: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get nutritional information about a specific ingredient.
    
    Searches for the ingredient in the input foods database and returns the
    nutritional information for the raw ingredient entries that match.
    
    Args:
        ingredient: Ingredient name to search for
        limit: Maximum number of results to return
    """
    # Look for ingredient in descriptions
    foods = (
        food_service.session.query(Food)
        .filter(Food.description.ilike(f"%{ingredient}%"))
        .filter(Food.data_type.in_(["foundation_food", "sr_legacy_food", "survey_fndds_food"]))
        .limit(limit * 2)
        .all()
    )
    
    # Format results
    results = [food_service._format_food_info(food) for food in foods]
    return [result.model_dump() for result in results[:limit]]


@mcp.tool()
async def search_foods_by_nutrient_content(nutrient_name: str, min_amount: float = 0, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search for foods with a minimum amount of a specific nutrient.
    
    Args:
        nutrient_name: Name of the nutrient to search for
        min_amount: Minimum amount of the nutrient per 100g
        limit: Maximum number of results to return
    """
    # Find the nutrient ID
    nutrient = (
        food_service.session.query(Nutrient)
        .filter(Nutrient.name.ilike(f"%{nutrient_name}%"))
        .first()
    )
    
    if not nutrient:
        return []
    
    # Get foods with that nutrient above the minimum amount
    food_nutrients = (
        food_service.session.query(FoodNutrient)
        .filter(FoodNutrient.nutrient_id == nutrient.id)
        .filter(FoodNutrient.amount >= min_amount)
        .order_by(FoodNutrient.amount.desc())
        .limit(limit)
        .all()
    )
    
    # Get the food objects
    food_ids = [fn.fdc_id for fn in food_nutrients]
    foods = food_service.session.query(Food).filter(Food.fdc_id.in_(food_ids)).all()
    
    # Order the foods to match the order of the nutrient values
    food_map = {food.fdc_id: food for food in foods}
    ordered_foods = [food_map[fdc_id] for fdc_id in food_ids if fdc_id in food_map]
    
    # Format results
    results = [food_service._format_food_info(food) for food in ordered_foods]
    return [result.model_dump() for result in results]


def run_server():
    """Run the MCP server."""
    # Start the MCP server
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()