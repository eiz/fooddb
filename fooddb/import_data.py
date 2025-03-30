import csv
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from sqlalchemy import delete
from sqlalchemy.orm import Session

from fooddb.models import Food, FoodNutrient, FoodPortion, Nutrient, Base, get_db_session, init_db
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
    
    # Create indexes for better query performance
    print("Creating indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_nutrient_fdc_id ON food_nutrient(fdc_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_portion_fdc_id ON food_portion(fdc_id)")
    
    # Commit and close
    conn.commit()
    conn.close()
    print("Fast import completed")


def nuke_database(db_path: str):
    """Clear all data from the database"""
    print("Nuking database...")
    session, engine = get_db_session(db_path)
    
    # Delete all data from tables
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