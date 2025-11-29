"""
Error handling utilities for Marimo dashboards.
Provides consistent error handling and fallback mechanisms.
"""

import marimo as mo
import pandas as pd
from typing import Optional, Dict, Any, Callable
import logging
from .common import create_error_message, create_warning_message, create_info_message

logger = logging.getLogger(__name__)


class DashboardErrorHandler:
    """Handles errors and provides fallbacks for dashboard operations."""
    
    def __init__(self, dashboard_name: str, account_id: Optional[str] = None):
        """Initialize error handler for a specific dashboard."""
        self.dashboard_name = dashboard_name
        self.account_id = account_id
    
    def handle_missing_account(self) -> mo.Html:
        """Handle missing account ID error."""
        return create_error_message(
            "Missing Account ID",
            f"No account ID specified for {self.dashboard_name}.",
            "Please navigate from the index page or add ?account_id=YOUR_ACCOUNT_ID to the URL."
        )
    
    def handle_no_data(self, job_type: str, days: int = 30) -> mo.Html:
        """Handle no data available error."""
        return create_info_message(
            "No Data Available",
            f"No {job_type} data found for account {self.account_id} in the last {days} days. "
            "Data may not have been extracted yet or the account may not have any activity."
        )
    
    def handle_database_error(self, error: Exception) -> mo.Html:
        """Handle database connection or query errors."""
        logger.error(f"Database error in {self.dashboard_name}: {error}")
        return create_error_message(
            "Database Error",
            f"Unable to retrieve data for {self.dashboard_name}.",
            "Please check the database connection and try again. Contact your administrator if the problem persists."
        )
    
    def handle_invalid_job_type(self, job_type: str) -> mo.Html:
        """Handle invalid or unregistered job type."""
        return create_warning_message(
            "Invalid Job Type",
            f"The job type '{job_type}' is not registered in the system.",
            "Please check the data_job_types table or contact your administrator."
        )
    
    def safe_execute(self, operation: Callable, fallback_value: Any = None, error_message: str = "Operation failed") -> Any:
        """Safely execute an operation with error handling."""
        try:
            return operation()
        except Exception as e:
            logger.error(f"Error in {self.dashboard_name}: {e}")
            if fallback_value is not None:
                return fallback_value
            else:
                return create_error_message(
                    "Operation Error",
                    error_message,
                    "Please try refreshing the page or contact your administrator."
                )
    
    def validate_data_quality(self, data: pd.DataFrame, required_columns: list) -> Optional[mo.Html]:
        """Validate data quality and return warning if issues found."""
        if data.empty:
            return None
        
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            return create_warning_message(
                "Data Quality Issue",
                f"Some expected columns are missing: {', '.join(missing_columns)}",
                "Some features may not work correctly. Please check the data extraction process."
            )
        
        # Check for null values in critical columns
        critical_nulls = []
        for col in required_columns:
            if col in data.columns and data[col].isnull().all():
                critical_nulls.append(col)
        
        if critical_nulls:
            return create_warning_message(
                "Data Quality Issue",
                f"These columns contain no data: {', '.join(critical_nulls)}",
                "Some visualizations may be empty or incorrect."
            )
        
        return None


def create_dashboard_error_handler(dashboard_name: str, account_id: Optional[str] = None) -> DashboardErrorHandler:
    """Create an error handler for a dashboard."""
    return DashboardErrorHandler(dashboard_name, account_id)


def safe_dashboard_operation(operation: Callable, error_handler: DashboardErrorHandler, 
                           fallback_value: Any = None, error_message: str = "Operation failed") -> Any:
    """Decorator-like function for safe dashboard operations."""
    return error_handler.safe_execute(operation, fallback_value, error_message)