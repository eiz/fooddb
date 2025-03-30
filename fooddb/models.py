from datetime import date
from typing import List, Optional

from sqlalchemy import (
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
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


def get_db_session(db_path: str = "sqlite:///fooddb.sqlite"):
    """Create a database session."""
    engine = create_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session(), engine


def init_db(engine):
    """Create all tables in the database."""
    Base.metadata.create_all(engine)