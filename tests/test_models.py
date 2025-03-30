import os
import tempfile
import unittest.mock
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from fooddb.models import (
    Base,
    Food,
    FoodNutrient,
    FoodPortion,
    Nutrient,
    get_db_session,
    init_db,
)
from fooddb.embeddings import generate_batch_embeddings


def test_db_initialization():
    """Test database initialization and basic models."""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        db_path = f"sqlite:///{tmp.name}"
        
        # Initialize database
        session, engine = get_db_session(db_path)
        init_db(engine)
        
        # Test inserting and querying a food
        food = Food(
            fdc_id=12345,
            data_type="test",
            description="Test Food",
            food_category_id="Test Category",
            publication_date=None,
        )
        session.add(food)
        session.commit()
        
        # Query the food
        queried_food = session.query(Food).filter(Food.fdc_id == 12345).one()
        assert queried_food.description == "Test Food"
        
        # Test inserting and querying a nutrient
        nutrient = Nutrient(
            id=67890,
            name="Test Nutrient",
            unit_name="g",
            nutrient_nbr="123",
            rank=1.0,
        )
        session.add(nutrient)
        session.commit()
        
        # Add a food nutrient relationship
        food_nutrient = FoodNutrient(
            id=55555,
            fdc_id=12345,
            nutrient_id=67890,
            amount=42.0,
        )
        session.add(food_nutrient)
        session.commit()
        
        # Add a food portion
        food_portion = FoodPortion(
            id=77777,
            fdc_id=12345,
            seq_num=1,
            amount=1.0,
            measure_unit_id="serving",
            portion_description="Test portion",
            modifier="cup",
            gram_weight=100.0,
        )
        session.add(food_portion)
        session.commit()
        
        # Verify relationships
        queried_food = session.query(Food).filter(Food.fdc_id == 12345).one()
        assert len(queried_food.nutrients) == 1
        assert queried_food.nutrients[0].amount == 42.0
        assert queried_food.nutrients[0].nutrient.name == "Test Nutrient"
        
        assert len(queried_food.portions) == 1
        assert queried_food.portions[0].gram_weight == 100.0
        assert queried_food.portions[0].modifier == "cup"
        
        # Clean up
        session.close()


def test_parallel_embedding_implementation():
    """Test the parallel embedding implementation directly."""
    # Test the process_embedding_batch function directly
    with unittest.mock.patch('fooddb.embeddings.client') as mock_client:
        # Mock the response from OpenAI
        mock_response = unittest.mock.MagicMock()
        mock_response.data = [
            unittest.mock.MagicMock(embedding=[0.1] * 1536),
            unittest.mock.MagicMock(embedding=[0.2] * 1536),
        ]
        mock_client.embeddings.create.return_value = mock_response
        
        # Mock the store_embedding function to avoid actual DB calls
        with unittest.mock.patch('fooddb.embeddings.store_embedding', return_value=True):
            from fooddb.embeddings import process_embedding_batch
            
            # Test the batch processing function
            batch = [(1, "apple"), (2, "banana")]
            result = process_embedding_batch(batch, "test-model", "test.db")
            
            # Verify it called the OpenAI API correctly
            mock_client.embeddings.create.assert_called_once()
            assert result == 2  # Should have processed 2 embeddings
            
    # Test with a very short timeout and verify it works correctly
    with unittest.mock.patch('fooddb.embeddings.client', return_value=None) as mock_client:
        # Make sure the client appears to be initialized
        mock_client.__bool__.return_value = True
        
        # We'll directly test the code path selection based on the parallel parameter
        with unittest.mock.patch('fooddb.embeddings.sqlite3.connect') as mock_connect:
            # Setup mock cursor
            mock_cursor = unittest.mock.MagicMock()
            mock_connect.return_value.cursor.return_value = mock_cursor
            
            # Mock the query results
            mock_cursor.fetchone.return_value = [10]  # 10 items need embeddings
            mock_cursor.fetchall.return_value = [(1, "apple"), (2, "banana"), (3, "carrot")]
            
            # Patch time to manipulate timing checks
            with unittest.mock.patch('time.time') as mock_time:
                # Setup a sequence of time returns: start, check timeout (exceeds limit), should exit
                mock_time.side_effect = [0, 10, 20]  # Start=0, Check=10 (> timeout), Exit=20
                
                # Patch logger to check for timeout message
                with unittest.mock.patch('fooddb.embeddings.logger') as mock_logger:
                    # Import here to use patched versions
                    from fooddb.embeddings import generate_batch_embeddings
                    
                    # Test with a 5-second timeout (should exit immediately since our mocked time jumps to 10)
                    generate_batch_embeddings(batch_size=5, timeout=5)
                    
                    # Verify the logger was called with timeout message
                    mock_logger.warning.assert_any_call("Timeout reached after 5 seconds. Stopping.")
        
            # Now check the sequential vs. parallel code paths
            with unittest.mock.patch('fooddb.embeddings.process_embedding_batch') as mock_process:
                # Also mock ThreadPoolExecutor
                with unittest.mock.patch('concurrent.futures.ThreadPoolExecutor') as mock_pool:
                    # Set up the mock so we can check if it was created with correct workers
                    mock_executor = unittest.mock.MagicMock()
                    mock_pool.return_value.__enter__.return_value = mock_executor
                    
                    # Import here to use patched versions
                    from fooddb.embeddings import generate_batch_embeddings
                    
                    # Reset time to normal for these tests
                    with unittest.mock.patch('time.time', return_value=0):
                        # Test with parallel = 3 (should use ThreadPoolExecutor)
                        mock_process.reset_mock()
                        mock_pool.reset_mock()
                        
                        try:
                            # We don't need the function to complete, just verify the execution path
                            generate_batch_embeddings(batch_size=5, parallel=3, timeout=5)
                        except Exception:
                            # Ignore any exceptions from mocked execution
                            pass
                        
                        # Verify ThreadPoolExecutor was created with correct number of workers
                        mock_pool.assert_called_once_with(max_workers=3)
                        
                        # Reset the mocks
                        mock_process.reset_mock()
                        mock_pool.reset_mock()
                        
                        # Test with parallel = 1 (should NOT use ThreadPoolExecutor)
                        try:
                            # We don't need the function to complete, just verify the execution path
                            generate_batch_embeddings(batch_size=5, parallel=1, timeout=5)
                        except Exception:
                            # Ignore any exceptions from mocked execution
                            pass
                        
                        # Verify ThreadPoolExecutor was NOT called in sequential mode
                        mock_pool.assert_not_called()


def test_vector_search():
    """Test the vector search functionality."""
    # Use mocks to simulate the search behavior without actual API calls
    with unittest.mock.patch('fooddb.embeddings.generate_embedding') as mock_generate_embedding:
        # Create a mock embedding vector
        mock_embedding = [0.1] * 1536
        mock_generate_embedding.return_value = mock_embedding
        
        # Mock the database connection and queries
        with unittest.mock.patch('fooddb.embeddings.connect_db') as mock_connect_db:
            mock_conn = unittest.mock.MagicMock()
            mock_connect_db.return_value = mock_conn
            
            # Set up the mock cursor and query results
            mock_cursor = unittest.mock.MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock query results (3 sample foods with similarity scores)
            mock_results = [
                (1001, "Apples, raw, with skin", 0.92),
                (1002, "Applesauce, unsweetened", 0.87),
                (1003, "Apple juice, unsweetened", 0.78)
            ]
            mock_cursor.fetchall.return_value = mock_results
            
            # Use execute_query as the query executor (which our mocks need to intercept)
            with unittest.mock.patch('fooddb.embeddings.execute_query') as mock_execute:
                mock_execute.return_value = mock_cursor
                
                # Import the function to test
                from fooddb.embeddings import search_food_by_text
                
                # Test the search function
                results = search_food_by_text("apple", 10, "dummy-model", "test.db")
                
                # Verify the correct embedding was generated
                mock_generate_embedding.assert_called_once_with("apple", "dummy-model")
                
                # Verify search returned the expected results
                assert results == mock_results
                assert len(results) == 3
                
                # Verify the results are sorted by similarity descending
                assert results[0][2] >= results[1][2] >= results[2][2]