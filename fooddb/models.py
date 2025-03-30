# Standard library imports
import os
import pathlib

# Third-party imports
from sqlalchemy import (
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Food(Base):
    __tablename__ = "food"

    fdc_id = Column(Integer, primary_key=True)
    data_type = Column(String)
    description = Column(String)
    food_category_id = Column(String)
    publication_date = Column(Date)

    nutrients = relationship("FoodNutrient", back_populates="food")
    portions = relationship("FoodPortion", back_populates="food")
    branded_food = relationship("BrandedFood", back_populates="food", uselist=False)
    components = relationship("FoodComponent", back_populates="food")
    input_foods = relationship("InputFood", back_populates="food")


class Nutrient(Base):
    __tablename__ = "nutrient"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    unit_name = Column(String)
    nutrient_nbr = Column(String)
    rank = Column(Float)

    food_nutrients = relationship("FoodNutrient", back_populates="nutrient")


class FoodNutrient(Base):
    __tablename__ = "food_nutrient"

    id = Column(Integer, primary_key=True)
    fdc_id = Column(Integer, ForeignKey("food.fdc_id"))
    nutrient_id = Column(Integer, ForeignKey("nutrient.id"))
    amount = Column(Float)
    
    food = relationship("Food", back_populates="nutrients")
    nutrient = relationship("Nutrient", back_populates="food_nutrients")


class FoodPortion(Base):
    __tablename__ = "food_portion"

    id = Column(Integer, primary_key=True)
    fdc_id = Column(Integer, ForeignKey("food.fdc_id"))
    seq_num = Column(Integer)
    amount = Column(Float)
    measure_unit_id = Column(String)
    portion_description = Column(String)
    modifier = Column(String)
    gram_weight = Column(Float)
    
    food = relationship("Food", back_populates="portions")


class BrandedFood(Base):
    __tablename__ = "branded_food"

    fdc_id = Column(Integer, ForeignKey("food.fdc_id"), primary_key=True)
    brand_owner = Column(String)
    brand_name = Column(String)
    subbrand_name = Column(String)
    gtin_upc = Column(String)
    ingredients = Column(Text)
    not_a_significant_source_of = Column(String)
    serving_size = Column(Float)
    serving_size_unit = Column(String)
    household_serving_fulltext = Column(String)
    branded_food_category = Column(String)
    data_source = Column(String)
    package_weight = Column(String)
    modified_date = Column(Date)
    available_date = Column(Date)
    market_country = Column(String)
    discontinued_date = Column(Date)
    preparation_state_code = Column(String)
    trade_channel = Column(String)
    short_description = Column(String)
    
    food = relationship("Food", back_populates="branded_food")


class FoodComponent(Base):
    __tablename__ = "food_component"

    id = Column(Integer, primary_key=True)
    fdc_id = Column(Integer, ForeignKey("food.fdc_id"))
    name = Column(String)
    pct_weight = Column(Float)
    is_refuse = Column(Boolean)
    gram_weight = Column(Float)
    data_points = Column(Integer)
    min_year_acquired = Column(Integer)
    
    food = relationship("Food", back_populates="components")


class InputFood(Base):
    __tablename__ = "input_food"

    id = Column(Integer, primary_key=True)
    fdc_id = Column(Integer, ForeignKey("food.fdc_id"))
    fdc_id_of_input_food = Column(Integer)
    seq_num = Column(Integer)
    amount = Column(Float)
    sr_code = Column(String)
    sr_description = Column(String)
    unit = Column(String)
    portion_code = Column(String)
    portion_description = Column(String)
    gram_weight = Column(Float)
    retention_code = Column(String)
    
    food = relationship("Food", back_populates="input_foods")


# Get the directory where the project root is located
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.absolute()
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "fooddb.sqlite")

def make_db_url(file_path: str) -> str:
    """Convert a file path to a SQLAlchemy SQLite URL."""
    if file_path.startswith('sqlite:///'):
        return file_path
    return f"sqlite:///{file_path}"


def get_db_session(db_path: str = None):
    """Create a database session."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    db_url = make_db_url(db_path)
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    return Session(), engine


def init_db(engine):
    """Create all tables in the database."""
    Base.metadata.create_all(engine)


def generate_food_info(food_id: int, db_path: str = None) -> str:
    """
    Generate detailed information about a specific food by its ID.
    
    Args:
        food_id: The unique identifier for the food item
        db_path: SQLite database path
        
    Returns:
        Formatted string with food information
    """
    result = []
    try:
        # Create a database session
        session, _ = get_db_session(db_path)
        
        # Query the food item with all related data
        food = session.query(Food).filter(Food.fdc_id == food_id).first()
        
        if not food:
            return f"❌ Food with ID {food_id} not found in database."
        
        # Display basic food information
        result.append("\n" + "=" * 80)
        result.append(f"🍽️  FOOD DETAILS: {food.description} (ID: {food.fdc_id})")
        result.append("=" * 80)
        result.append(f"Type: {food.data_type}")
        if food.food_category_id:
            result.append(f"Category: {food.food_category_id}")
        if food.publication_date:
            result.append(f"Publication Date: {food.publication_date}")
        result.append("")
        
        # Display branded food information if available
        if food.branded_food:
            bf = food.branded_food
            result.append("📋 BRANDED FOOD INFORMATION")
            result.append("-" * 80)
            if bf.brand_owner:
                result.append(f"Brand Owner: {bf.brand_owner}")
            if bf.brand_name:
                result.append(f"Brand Name: {bf.brand_name}")
            if bf.branded_food_category:
                result.append(f"Category: {bf.branded_food_category}")
            if bf.gtin_upc:
                result.append(f"UPC: {bf.gtin_upc}")
            if bf.serving_size:
                size_str = f"{bf.serving_size}"
                if bf.serving_size_unit:
                    size_str += f" {bf.serving_size_unit}"
                result.append(f"Serving Size: {size_str}")
            if bf.household_serving_fulltext:
                result.append(f"Household Serving: {bf.household_serving_fulltext}")
            if bf.ingredients:
                result.append(f"\nIngredients: {bf.ingredients}")
            result.append("")
        
        # Display nutrient information
        if food.nutrients:
            result.append("🧪 NUTRITION INFORMATION")
            result.append("-" * 80)
            # Sort nutrients by rank for more organized display
            sorted_nutrients = sorted(
                food.nutrients, 
                key=lambda fn: fn.nutrient.rank if fn.nutrient and fn.nutrient.rank else 9999
            )
            for fn in sorted_nutrients:
                if fn.nutrient and fn.amount:
                    result.append(f"{fn.nutrient.name:<30} {fn.amount:>8.2f} {fn.nutrient.unit_name}")
            result.append("")
        
        # Display portion information
        if food.portions:
            result.append("📏 SERVING SIZE INFORMATION")
            result.append("-" * 80)
            for portion in food.portions:
                portion_desc = []
                if portion.amount:
                    portion_desc.append(f"{portion.amount}")
                if portion.measure_unit_id:
                    portion_desc.append(portion.measure_unit_id)
                if portion.portion_description:
                    portion_desc.append(f"({portion.portion_description})")
                if portion.modifier:
                    portion_desc.append(portion.modifier)
                
                portion_str = " ".join(portion_desc)
                if portion.gram_weight:
                    result.append(f"{portion_str:<50} = {portion.gram_weight:>8.2f} g")
                else:
                    result.append(f"{portion_str}")
            result.append("")
        
        # Display food components
        if food.components:
            result.append("🧩 FOOD COMPONENTS")
            result.append("-" * 80)
            for comp in food.components:
                comp_info = []
                if comp.name:
                    comp_info.append(comp.name)
                if comp.pct_weight:
                    comp_info.append(f"{comp.pct_weight:.1f}%")
                if comp.gram_weight:
                    comp_info.append(f"{comp.gram_weight:.2f}g")
                if comp.is_refuse:
                    comp_info.append("(refuse)")
                    
                result.append(" - " + ", ".join(comp_info))
            result.append("")
        
        # Display input foods (for multi-ingredient foods)
        if food.input_foods:
            result.append("🧑‍🍳 INGREDIENTS/INPUT FOODS")
            result.append("-" * 80)
            for input_food in sorted(food.input_foods, key=lambda x: x.seq_num if x.seq_num else 9999):
                input_desc = []
                if input_food.sr_description:
                    input_desc.append(input_food.sr_description)
                elif input_food.fdc_id_of_input_food:
                    input_desc.append(f"Food #{input_food.fdc_id_of_input_food}")
                
                if input_food.amount:
                    amount_str = f"{input_food.amount}"
                    if input_food.unit:
                        amount_str += f" {input_food.unit}"
                    input_desc.append(amount_str)
                
                if input_food.portion_description:
                    input_desc.append(f"({input_food.portion_description})")
                
                if input_food.gram_weight:
                    input_desc.append(f"= {input_food.gram_weight:.2f}g")
                    
                result.append(" - " + " ".join(input_desc))
            result.append("")
            
    except Exception as e:
        return f"❌ Error retrieving food information: {e}"
    finally:
        session.close()
    
    return "\n".join(result)