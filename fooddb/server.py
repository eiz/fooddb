from typing import Any, Dict, List
import logging

from pydantic import BaseModel, Field

# Import the MCP server package
from mcp.server.fastmcp import FastMCP

from fooddb.models import get_db_session
from fooddb.embeddings import search_food_by_text

# Import default database path from models.py
from fooddb.models import DEFAULT_DB_PATH

# Configure logging
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("fooddb", description="USDA Food Database API for nutritional information")

# Simple result model for food search
class FoodSearchResult(BaseModel):
    """A simplified model for food search results."""
    id: int = Field(..., description="Food ID")
    name: str = Field(..., description="Food name/description")
    similarity: float = Field(..., description="Similarity score (0-1)")


class FoodDBService:
    def __init__(self, db_path=None):
        """Initialize the food database service."""
        # Use provided path or default to absolute path
        if db_path is None:
            db_path = DEFAULT_DB_PATH
            logger.info(f"Using default database path: {db_path}")
        
        # Initialize database connection
        self.session, _ = get_db_session(db_path)
        self.db_path = db_path
    
    async def food_search(self, query: str, limit: int = 10, model: str = "text-embedding-3-small") -> List[FoodSearchResult]:
        """
        Search for foods using semantic vector search.
        
        Args:
            query: The search term
            limit: Maximum number of results to return
            model: OpenAI embedding model to use
            
        Returns:
            List of matching food results with similarity scores
        """
        # Try vector search using embeddings
        try:
            # Use the same search function as the CLI command
            vector_results = search_food_by_text(query, limit=limit, model=model)
            
            if not vector_results:
                return []
                
            # Format results as FoodSearchResult objects
            results = []
            for fdc_id, description, similarity in vector_results:
                results.append(
                    FoodSearchResult(
                        id=fdc_id,
                        name=description,
                        similarity=similarity
                    )
                )
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []


# Initialize the service
food_service = FoodDBService()


# Register MCP tool
@mcp.tool()
async def food_search(query: str, limit: int = 10, model: str = "text-embedding-3-small") -> List[Dict[str, Any]]:
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
    results = await food_service.food_search(query, limit, model)
    # Convert Pydantic models to dictionaries for MCP compatibility
    return [result.model_dump() for result in results]


def run_server():
    """Run the MCP server."""
    # Start the MCP server
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()