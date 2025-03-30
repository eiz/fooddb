"""
Test script for the ingredient functionality in the FoodDB.
"""
import sys
from pathlib import Path

# Add the project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fooddb.models import (
    Food,
    BrandedFood,
    FoodComponent,
    InputFood,
    get_db_session,
    init_db
)

def test_ingredients():
    """Test the ingredient functionality"""
    
    # Connect to database
    db_path = "sqlite:///test.db"
    session, engine = get_db_session(db_path)
    
    # Initialize database
    init_db(engine)
    
    # Check if we have branded food data
    branded_count = session.query(BrandedFood).count()
    print(f"Found {branded_count} branded foods")
    
    # Check if we have ingredient data
    ingredient_count = session.query(InputFood).count()
    print(f"Found {ingredient_count} input foods (ingredients)")
    
    # Check if we have component data
    component_count = session.query(FoodComponent).count()
    print(f"Found {component_count} food components")
    
    # If we have data, test some queries
    if branded_count > 0:
        # Get a branded food example with ingredients
        branded_food = session.query(BrandedFood).filter(BrandedFood.ingredients.is_not(None)).first()
        if branded_food:
            print(f"\nExample branded food: {branded_food.fdc_id}")
            
            # Get the actual food info
            food = session.query(Food).filter(Food.fdc_id == branded_food.fdc_id).first()
            if food:
                print(f"Food name: {food.description}")
                print(f"Brand owner: {branded_food.brand_owner}")
                print(f"Brand name: {branded_food.brand_name}")
                print(f"Ingredients: {branded_food.ingredients}")
    
    if ingredient_count > 0:
        # Get an example food with ingredients
        food_with_ingredients = (
            session.query(Food)
            .join(InputFood, Food.fdc_id == InputFood.fdc_id)
            .first()
        )
        
        if food_with_ingredients:
            print(f"\nExample food with ingredients: {food_with_ingredients.fdc_id}")
            print(f"Food name: {food_with_ingredients.description}")
            
            # Get the ingredients
            ingredients = (
                session.query(InputFood)
                .filter(InputFood.fdc_id == food_with_ingredients.fdc_id)
                .order_by(InputFood.seq_num)
                .all()
            )
            
            print("Ingredients:")
            for ing in ingredients:
                print(f"  - {ing.amount} {ing.unit} {ing.sr_description}")
    
    if component_count > 0:
        # Get an example food with components
        food_with_components = (
            session.query(Food)
            .join(FoodComponent, Food.fdc_id == FoodComponent.fdc_id)
            .first()
        )
        
        if food_with_components:
            print(f"\nExample food with components: {food_with_components.fdc_id}")
            print(f"Food name: {food_with_components.description}")
            
            # Get the components
            components = (
                session.query(FoodComponent)
                .filter(FoodComponent.fdc_id == food_with_components.fdc_id)
                .all()
            )
            
            print("Components:")
            for comp in components:
                refuse_str = "(refuse)" if comp.is_refuse else ""
                print(f"  - {comp.name}: {comp.pct_weight}% {comp.gram_weight}g {refuse_str}")

if __name__ == "__main__":
    test_ingredients()