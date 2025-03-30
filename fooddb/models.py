# No datetime import needed

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


def get_db_session(db_path: str = "sqlite:///fooddb.sqlite"):
    """Create a database session."""
    engine = create_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session(), engine


def init_db(engine):
    """Create all tables in the database."""
    Base.metadata.create_all(engine)