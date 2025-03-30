from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Union, cast

import pandas as pd
from pydantic import BaseModel, Field
from sqlalchemy import func, text
from sqlalchemy.orm import Session, joinedload

# Import the MCP server package
from mcp.server.fastmcp import FastMCP

from fooddb.models import Food, FoodNutrient, FoodPortion, Nutrient, get_db_session
from fooddb.embeddings import (
    setup_vector_db,
    generate_embedding,
    search_food_by_text,
    generate_batch_embeddings
)

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


class FoodInfo(BaseModel):
    id: int = Field(..., description="Food ID")
    name: str = Field(..., description="Food name/description")
    category: Optional[str] = Field(None, description="Food category")
    macros: Macros = Field(..., description="Macronutrient information")
    servings: List[ServingInfo] = Field(default_factory=list, description="Available serving sizes")


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
    
    def _format_food_info(self, food: Food) -> FoodInfo:
        """Format a food record into a FoodInfo response."""
        macros = self._get_macros_for_food(food.fdc_id)
        servings = self._get_servings_for_food(food.fdc_id)
        
        return FoodInfo(
            id=food.fdc_id,
            name=food.description,
            category=food.food_category_id,
            macros=macros,
            servings=servings
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


def run_server():
    """Run the MCP server."""
    # Start the MCP server
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()