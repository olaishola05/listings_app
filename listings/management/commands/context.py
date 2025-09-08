from django.db import transaction, connection
import time
from contextlib import contextmanager

from seed import logger


@contextmanager
def database_transaction():
    """Context manager for database transactions with rollback on error."""
    try:
        with transaction.atomic():
            logger.info("Starting database transaction")
            yield
            logger.info("Transaction committed successfully")
    except Exception as e:
        logger.error(f"Transaction rolled back due to error: {str(e)}")
        raise


@contextmanager
def performance_monitor(operation_name: str):
    """Context manager to monitor performance of operations."""
    start_time = time.time()
    start_memory = connection.queries_log.total_time if hasattr(connection, 'queries_log') else 0

    try:
        logger.info(f"Starting {operation_name}")
        yield
    finally:
        end_time = time.time()
        duration = end_time - start_time
        query_count = len(connection.queries) if connection.queries else 0
        logger.info(f"{operation_name} completed in {duration:.2f}s with {query_count} queries")
