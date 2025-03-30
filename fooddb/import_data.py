import csv
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from sqlalchemy import delete
from sqlalchemy.orm import Session

from fooddb.models import (
    Base, 
    Food, 
    FoodNutrient, 
    FoodPortion, 
    Nutrient, 
    BrandedFood, 
    FoodComponent,
    InputFood,
    get_db_session, 
    init_db
)
from fooddb.embeddings import setup_vector_db, generate_batch_embeddings


def parse_date(date_str: str) -> Optional[datetime.date]:
    """Parse date from string or return None if invalid."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_float(value: str) -> Optional[float]:
    """Parse float from string or return None if invalid."""
    if not value or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def import_nutrients(session: Session, csv_path: str) -> None:
    """Import nutrient data from CSV."""
    print(f"Importing nutrients from {csv_path}")
    
    # Use pandas for efficient CSV reading
    df = pd.read_csv(csv_path)
    
    # Convert to records for bulk insert
    records = []
    for _, row in df.iterrows():
        rank = parse_float(row["rank"]) if "rank" in row else None
        
        nutrient = Nutrient(
            id=int(row["id"]),
            name=row["name"],
            unit_name=row["unit_name"],
            nutrient_nbr=row["nutrient_nbr"],
            rank=rank,
        )
        records.append(nutrient)
    
    # Bulk insert
    session.bulk_save_objects(records)
    session.commit()
    print(f"Imported {len(records)} nutrients")


def import_foods(session: Session, csv_path: str) -> None:
    """Import food data from CSV."""
    print(f"Importing foods from {csv_path}")
    
    # Use pandas for efficient CSV reading
    df = pd.read_csv(csv_path)
    
    # Convert to records for bulk insert
    records = []
    for _, row in df.iterrows():
        publication_date = parse_date(row["publication_date"])
        
        food = Food(
            fdc_id=int(row["fdc_id"]),
            data_type=row["data_type"],
            description=row["description"],
            food_category_id=row["food_category_id"],
            publication_date=publication_date,
        )
        records.append(food)
    
    # Bulk insert
    session.bulk_save_objects(records)
    session.commit()
    print(f"Imported {len(records)} foods")


def import_food_nutrients(session: Session, csv_path: str) -> None:
    """Import food nutrient data from CSV."""
    print(f"Importing food nutrients from {csv_path}")
    
    # Use pandas for efficient CSV reading - use chunks for memory efficiency
    chunk_size = 100000
    chunks = pd.read_csv(csv_path, chunksize=chunk_size)
    
    total_imported = 0
    for chunk in chunks:
        records = []
        for _, row in chunk.iterrows():
            try:
                # Skip rows with missing essential data
                if pd.isna(row["fdc_id"]) or pd.isna(row["nutrient_id"]):
                    continue
                
                amount = parse_float(row["amount"])
                
                food_nutrient = FoodNutrient(
                    id=int(row["id"]),
                    fdc_id=int(row["fdc_id"]),
                    nutrient_id=int(row["nutrient_id"]),
                    amount=amount,
                )
                records.append(food_nutrient)
            except (ValueError, KeyError) as e:
                print(f"Error processing row: {row}, error: {e}")
                continue
        
        # Bulk insert
        session.bulk_save_objects(records)
        session.commit()
        total_imported += len(records)
        print(f"Imported chunk of {len(records)} food nutrients")
    
    print(f"Imported {total_imported} food nutrients in total")


def import_food_portions(session: Session, csv_path: str) -> None:
    """Import food portion data from CSV."""
    print(f"Importing food portions from {csv_path}")
    
    # Use pandas for efficient CSV reading
    df = pd.read_csv(csv_path)
    
    # Convert to records for bulk insert
    records = []
    for _, row in df.iterrows():
        try:
            # Skip rows with missing essential data
            if pd.isna(row["fdc_id"]):
                continue
            
            amount = parse_float(row["amount"])
            gram_weight = parse_float(row["gram_weight"])
            
            food_portion = FoodPortion(
                id=int(row["id"]),
                fdc_id=int(row["fdc_id"]),
                seq_num=int(row["seq_num"]) if not pd.isna(row["seq_num"]) else None,
                amount=amount,
                measure_unit_id=row["measure_unit_id"] if not pd.isna(row["measure_unit_id"]) else None,
                portion_description=row["portion_description"] if not pd.isna(row["portion_description"]) else None,
                modifier=row["modifier"] if not pd.isna(row["modifier"]) else None,
                gram_weight=gram_weight,
            )
            records.append(food_portion)
        except (ValueError, KeyError) as e:
            print(f"Error processing row: {row}, error: {e}")
            continue
    
    # Bulk insert
    session.bulk_save_objects(records)
    session.commit()
    print(f"Imported {len(records)} food portions")


def import_branded_foods(session: Session, csv_path: str) -> None:
    """Import branded food data from CSV."""
    print(f"Importing branded foods from {csv_path}")
    
    # Use pandas for efficient CSV reading - use chunks for memory efficiency
    chunk_size = 100000
    chunks = pd.read_csv(csv_path, chunksize=chunk_size)
    
    total_imported = 0
    for chunk in chunks:
        records = []
        for _, row in chunk.iterrows():
            try:
                # Skip rows with missing essential data
                if pd.isna(row["fdc_id"]):
                    continue
                
                # Parse dates
                modified_date = parse_date(row["modified_date"]) if "modified_date" in row and not pd.isna(row["modified_date"]) else None
                available_date = parse_date(row["available_date"]) if "available_date" in row and not pd.isna(row["available_date"]) else None
                discontinued_date = parse_date(row["discontinued_date"]) if "discontinued_date" in row and not pd.isna(row["discontinued_date"]) else None
                
                # Parse numeric values
                serving_size = parse_float(row["serving_size"]) if "serving_size" in row and not pd.isna(row["serving_size"]) else None
                
                # Create branded food object
                branded_food = BrandedFood(
                    fdc_id=int(row["fdc_id"]),
                    brand_owner=row["brand_owner"] if "brand_owner" in row and not pd.isna(row["brand_owner"]) else None,
                    brand_name=row["brand_name"] if "brand_name" in row and not pd.isna(row["brand_name"]) else None,
                    subbrand_name=row["subbrand_name"] if "subbrand_name" in row and not pd.isna(row["subbrand_name"]) else None,
                    gtin_upc=row["gtin_upc"] if "gtin_upc" in row and not pd.isna(row["gtin_upc"]) else None,
                    ingredients=row["ingredients"] if "ingredients" in row and not pd.isna(row["ingredients"]) else None,
                    not_a_significant_source_of=row["not_a_significant_source_of"] if "not_a_significant_source_of" in row and not pd.isna(row["not_a_significant_source_of"]) else None,
                    serving_size=serving_size,
                    serving_size_unit=row["serving_size_unit"] if "serving_size_unit" in row and not pd.isna(row["serving_size_unit"]) else None,
                    household_serving_fulltext=row["household_serving_fulltext"] if "household_serving_fulltext" in row and not pd.isna(row["household_serving_fulltext"]) else None,
                    branded_food_category=row["branded_food_category"] if "branded_food_category" in row and not pd.isna(row["branded_food_category"]) else None,
                    data_source=row["data_source"] if "data_source" in row and not pd.isna(row["data_source"]) else None,
                    package_weight=row["package_weight"] if "package_weight" in row and not pd.isna(row["package_weight"]) else None,
                    modified_date=modified_date,
                    available_date=available_date,
                    market_country=row["market_country"] if "market_country" in row and not pd.isna(row["market_country"]) else None,
                    discontinued_date=discontinued_date,
                    preparation_state_code=row["preparation_state_code"] if "preparation_state_code" in row and not pd.isna(row["preparation_state_code"]) else None,
                    trade_channel=row["trade_channel"] if "trade_channel" in row and not pd.isna(row["trade_channel"]) else None,
                    short_description=row["short_description"] if "short_description" in row and not pd.isna(row["short_description"]) else None,
                )
                records.append(branded_food)
            except (ValueError, KeyError) as e:
                print(f"Error processing row: {e}")
                continue
        
        # Bulk insert
        session.bulk_save_objects(records)
        session.commit()
        total_imported += len(records)
        print(f"Imported chunk of {len(records)} branded foods")
    
    print(f"Imported {total_imported} branded foods in total")


def import_food_components(session: Session, csv_path: str) -> None:
    """Import food component data from CSV."""
    print(f"Importing food components from {csv_path}")
    
    # Use pandas for efficient CSV reading
    df = pd.read_csv(csv_path)
    
    # Convert to records for bulk insert
    records = []
    for _, row in df.iterrows():
        try:
            # Skip rows with missing essential data
            if pd.isna(row["fdc_id"]):
                continue
            
            # Parse numeric values
            pct_weight = parse_float(row["pct_weight"]) if "pct_weight" in row and not pd.isna(row["pct_weight"]) else None
            gram_weight = parse_float(row["gram_weight"]) if "gram_weight" in row and not pd.isna(row["gram_weight"]) else None
            data_points = int(row["data_points"]) if "data_points" in row and not pd.isna(row["data_points"]) else None
            min_year_acquired = int(row["min_year_acquired"]) if "min_year_acquired" in row and not pd.isna(row["min_year_acquired"]) else None
            
            # Parse boolean values
            is_refuse = row["is_refuse"].upper() == "Y" if "is_refuse" in row and not pd.isna(row["is_refuse"]) else None
            
            food_component = FoodComponent(
                id=int(row["id"]),
                fdc_id=int(row["fdc_id"]),
                name=row["name"] if "name" in row and not pd.isna(row["name"]) else None,
                pct_weight=pct_weight,
                is_refuse=is_refuse,
                gram_weight=gram_weight,
                data_points=data_points,
                min_year_acquired=min_year_acquired,
            )
            records.append(food_component)
        except (ValueError, KeyError) as e:
            print(f"Error processing row: {row}, error: {e}")
            continue
    
    # Bulk insert
    session.bulk_save_objects(records)
    session.commit()
    print(f"Imported {len(records)} food components")


def import_input_foods(session: Session, csv_path: str) -> None:
    """Import input food data from CSV."""
    print(f"Importing input foods from {csv_path}")
    
    # Use pandas for efficient CSV reading
    df = pd.read_csv(csv_path)
    
    # Convert to records for bulk insert
    records = []
    for _, row in df.iterrows():
        try:
            # Skip rows with missing essential data
            if pd.isna(row["fdc_id"]):
                continue
            
            # Parse numeric values
            amount = parse_float(row["amount"]) if "amount" in row and not pd.isna(row["amount"]) else None
            gram_weight = parse_float(row["gram_weight"]) if "gram_weight" in row and not pd.isna(row["gram_weight"]) else None
            fdc_id_of_input_food = int(row["fdc_id_of_input_food"]) if "fdc_id_of_input_food" in row and not pd.isna(row["fdc_id_of_input_food"]) and row["fdc_id_of_input_food"] != "" else None
            
            input_food = InputFood(
                id=int(row["id"]),
                fdc_id=int(row["fdc_id"]),
                fdc_id_of_input_food=fdc_id_of_input_food,
                seq_num=int(row["seq_num"]) if "seq_num" in row and not pd.isna(row["seq_num"]) else None,
                amount=amount,
                sr_code=row["sr_code"] if "sr_code" in row and not pd.isna(row["sr_code"]) else None,
                sr_description=row["sr_description"] if "sr_description" in row and not pd.isna(row["sr_description"]) else None,
                unit=row["unit"] if "unit" in row and not pd.isna(row["unit"]) else None,
                portion_code=row["portion_code"] if "portion_code" in row and not pd.isna(row["portion_code"]) else None,
                portion_description=row["portion_description"] if "portion_description" in row and not pd.isna(row["portion_description"]) else None,
                gram_weight=gram_weight,
                retention_code=row["retention_code"] if "retention_code" in row and not pd.isna(row["retention_code"]) else None,
            )
            records.append(input_food)
        except (ValueError, KeyError) as e:
            print(f"Error processing row: {row}, error: {e}")
            continue
    
    # Bulk insert
    session.bulk_save_objects(records)
    session.commit()
    print(f"Imported {len(records)} input foods")


def fast_bulk_import(db_path: str, data_dir: str):
    """Use direct SQLite connection for faster imports"""
    print("Using fast direct SQLite import...")
    
    # Extract SQLite path from SQLAlchemy connection string
    if db_path.startswith('sqlite:///'):
        sqlite_path = db_path[10:]
    else:
        sqlite_path = db_path
    
    # Connect directly to SQLite
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    session, engine = get_db_session(db_path)
    init_db(engine)
    
    # Get table metadata to ensure we only include valid columns
    nutrient_columns = [c.name for c in Nutrient.__table__.columns]
    food_columns = [c.name for c in Food.__table__.columns]
    food_nutrient_columns = [c.name for c in FoodNutrient.__table__.columns]
    food_portion_columns = [c.name for c in FoodPortion.__table__.columns]
    branded_food_columns = [c.name for c in BrandedFood.__table__.columns]
    food_component_columns = [c.name for c in FoodComponent.__table__.columns]
    input_food_columns = [c.name for c in InputFood.__table__.columns]
    
    session.close()
    
    # Import nutrients
    print("Importing nutrients...")
    nutrient_df = pd.read_csv(os.path.join(data_dir, "nutrient.csv"))
    # Keep only columns that match our model
    valid_nutrient_cols = [col for col in nutrient_df.columns if col in nutrient_columns]
    nutrient_df = nutrient_df[valid_nutrient_cols]
    nutrient_df.to_sql('nutrient', conn, if_exists='append', index=False)
    
    # Import foods
    print("Importing foods...")
    food_df = pd.read_csv(os.path.join(data_dir, "food.csv"))
    # Convert publication_date to proper date format
    if 'publication_date' in food_df.columns:
        # Use flexible date parsing
        food_df['publication_date'] = pd.to_datetime(food_df['publication_date'], 
                                                    format='mixed', 
                                                    errors='coerce').dt.date
    # Keep only columns that match our model
    valid_food_cols = [col for col in food_df.columns if col in food_columns]
    food_df = food_df[valid_food_cols]
    food_df.to_sql('food', conn, if_exists='append', index=False)
    
    # Import food nutrients (in chunks due to size)
    print("Importing food nutrients...")
    chunk_size = 100000
    for i, chunk in enumerate(pd.read_csv(os.path.join(data_dir, "food_nutrient.csv"), chunksize=chunk_size)):
        # Keep only columns that match our model
        valid_nutrient_cols = [col for col in chunk.columns if col in food_nutrient_columns]
        chunk = chunk[valid_nutrient_cols]
        chunk.to_sql('food_nutrient', conn, if_exists='append', index=False)
        print(f"Imported chunk {i+1}: {len(chunk)} food nutrient records")
    
    # Import food portions
    print("Importing food portions...")
    portion_df = pd.read_csv(os.path.join(data_dir, "food_portion.csv"))
    # Keep only columns that match our model
    valid_portion_cols = [col for col in portion_df.columns if col in food_portion_columns]
    portion_df = portion_df[valid_portion_cols]
    portion_df.to_sql('food_portion', conn, if_exists='append', index=False)
    
    # Import branded foods (in chunks due to size)
    if os.path.exists(os.path.join(data_dir, "branded_food.csv")):
        print("Importing branded foods...")
        chunk_size = 100000
        for i, chunk in enumerate(pd.read_csv(os.path.join(data_dir, "branded_food.csv"), chunksize=chunk_size)):
            # Convert date columns
            date_columns = ['modified_date', 'available_date', 'discontinued_date']
            for col in date_columns:
                if col in chunk.columns:
                    chunk[col] = pd.to_datetime(chunk[col], format='mixed', errors='coerce').dt.date
            
            # Keep only columns that match our model
            valid_cols = [col for col in chunk.columns if col in branded_food_columns]
            chunk = chunk[valid_cols]
            chunk.to_sql('branded_food', conn, if_exists='append', index=False)
            print(f"Imported chunk {i+1}: {len(chunk)} branded food records")
    
    # Import food components
    if os.path.exists(os.path.join(data_dir, "food_component.csv")):
        print("Importing food components...")
        component_df = pd.read_csv(os.path.join(data_dir, "food_component.csv"))
        
        # Process boolean column
        if 'is_refuse' in component_df.columns:
            component_df['is_refuse'] = component_df['is_refuse'].apply(lambda x: True if str(x).upper() == 'Y' else False)
        
        # Keep only columns that match our model
        valid_cols = [col for col in component_df.columns if col in food_component_columns]
        component_df = component_df[valid_cols]
        component_df.to_sql('food_component', conn, if_exists='append', index=False)
        print(f"Imported {len(component_df)} food component records")
    
    # Import input foods
    if os.path.exists(os.path.join(data_dir, "input_food.csv")):
        print("Importing input foods...")
        input_df = pd.read_csv(os.path.join(data_dir, "input_food.csv"))
        
        # Keep only columns that match our model
        valid_cols = [col for col in input_df.columns if col in input_food_columns]
        input_df = input_df[valid_cols]
        input_df.to_sql('input_food', conn, if_exists='append', index=False)
        print(f"Imported {len(input_df)} input food records")
    
    # Create indexes for better query performance
    print("Creating indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_nutrient_fdc_id ON food_nutrient(fdc_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_portion_fdc_id ON food_portion(fdc_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_component_fdc_id ON food_component(fdc_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_input_food_fdc_id ON input_food(fdc_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_branded_food_ingredients ON branded_food(ingredients)")
    
    # Commit and close
    conn.commit()
    conn.close()
    print("Fast import completed")


def nuke_database(db_path: str):
    """Clear all data from the database"""
    print("Nuking database...")
    session, engine = get_db_session(db_path)
    
    # Delete all data from tables
    session.execute(delete(InputFood))
    session.execute(delete(FoodComponent))
    session.execute(delete(BrandedFood))
    session.execute(delete(FoodPortion))
    session.execute(delete(FoodNutrient))
    session.execute(delete(Food))
    session.execute(delete(Nutrient))
    
    session.commit()
    session.close()
    print("Database nuked")


def import_all_data(
    data_dir: str = "./data", 
    db_path: str = "sqlite:///fooddb.sqlite", 
    nuke: bool = False, 
    fast: bool = True, 
    create_embeddings: bool = True,
    parallel: int = 1,
    timeout: int = 600  # Default timeout in seconds (10 minutes)
):
    """
    Import all data from CSV files in the specified directory.
    
    Args:
        data_dir: Directory containing CSV files
        db_path: Path to SQLite database
        nuke: Whether to clear all data before importing
        fast: Whether to use fast direct import (True) or ORM import (False)
        create_embeddings: Whether to generate embeddings after import
        parallel: Number of parallel API requests for embeddings generation
        timeout: Maximum execution time for embedding generation in seconds
    """
    # Nuke database if requested
    if nuke:
        nuke_database(db_path)
    
    if fast:
        # Use fast direct import
        fast_bulk_import(db_path, data_dir)
    else:
        # Use SQLAlchemy ORM import (slower but more reliable)
        session, engine = get_db_session(db_path)
        
        # Initialize database (create tables)
        init_db(engine)
        
        # Import data
        import_nutrients(session, os.path.join(data_dir, "nutrient.csv"))
        import_foods(session, os.path.join(data_dir, "food.csv"))
        import_food_nutrients(session, os.path.join(data_dir, "food_nutrient.csv"))
        import_food_portions(session, os.path.join(data_dir, "food_portion.csv"))
        
        # Import ingredient-related data if available
        if os.path.exists(os.path.join(data_dir, "branded_food.csv")):
            import_branded_foods(session, os.path.join(data_dir, "branded_food.csv"))
        
        if os.path.exists(os.path.join(data_dir, "food_component.csv")):
            import_food_components(session, os.path.join(data_dir, "food_component.csv"))
        
        if os.path.exists(os.path.join(data_dir, "input_food.csv")):
            import_input_foods(session, os.path.join(data_dir, "input_food.csv"))
        
        session.close()
        print("Data import completed")
    
    # Set up vector database for embeddings
    if create_embeddings:
        print("Setting up vector database...")
        setup_vector_db(db_path)
        
        parallel_mode = "parallel" if parallel > 1 else "sequential"
        print(f"Generating initial batch of embeddings in {parallel_mode} mode ({parallel} workers)...")
        print(f"Embedding generation will timeout after {timeout} seconds")
        
        import time
        start_time = time.time()
        
        generate_batch_embeddings(
            batch_size=1000, 
            db_path=db_path, 
            parallel=parallel,
            timeout=timeout
        )
        
        elapsed_time = time.time() - start_time
        print(f"Embedding generation complete in {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    import_all_data()