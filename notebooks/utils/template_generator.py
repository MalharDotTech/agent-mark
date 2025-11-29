"""
Dashboard Template Generator for Marimo Notebooks
Provides utilities for creating reusable dashboard templates and dynamic job type discovery.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class JobTypeConfig:
    """Configuration for a data job type."""
    job_type_id: str
    job_name: str
    description: str
    table_name: str
    is_active: bool
    
    # Dashboard configuration
    primary_metrics: List[str]
    chart_types: List[str]
    default_filters: Dict[str, Any]
    
    @classmethod
    def from_db_row(cls, row: sqlite3.Row, dashboard_config: Optional[Dict] = None) -> 'JobTypeConfig':
        """Create JobTypeConfig from database row."""
        config = dashboard_config or {}
        
        return cls(
            job_type_id=row['job_type_id'],
            job_name=row['job_name'],
            description=row['description'],
            table_name=row['table_name'],
            is_active=bool(row['is_active']),
            primary_metrics=config.get('primary_metrics', ['impressions', 'clicks', 'spend']),
            chart_types=config.get('chart_types', ['time_series', 'bar_chart', 'table']),
            default_filters=config.get('default_filters', {'date_range': 30})
        )


class DashboardTemplateGenerator:
    """Generates dashboard templates for different job types."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize template generator with database path."""
        if db_path is None:
            self.db_path = Path(__file__).parent.parent.parent / "data" / "meta_ads.db"
        else:
            self.db_path = Path(db_path)
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def discover_job_types(self) -> List[JobTypeConfig]:
        """Discover available job types from database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT job_type_id, job_name, description, table_name, is_active
                    FROM data_job_types
                    WHERE is_active = 1
                    ORDER BY job_name
                """)
                
                job_types = []
                for row in cursor.fetchall():
                    # Get dashboard configuration for this job type
                    dashboard_config = self._get_dashboard_config(row['job_type_id'])
                    job_config = JobTypeConfig.from_db_row(row, dashboard_config)
                    job_types.append(job_config)
                
                return job_types
        except Exception as e:
            logger.error(f"Failed to discover job types: {e}")
            return []
    
    def _get_dashboard_config(self, job_type_id: str) -> Dict[str, Any]:
        """Get dashboard configuration for a specific job type."""
        # Default configurations for known job types
        configs = {
            'ad_performance': {
                'primary_metrics': ['impressions', 'clicks', 'spend', 'reach', 'ctr', 'cpc'],
                'chart_types': ['time_series', 'bar_chart', 'scatter_plot', 'table'],
                'default_filters': {'date_range': 30}
            },
            'campaign_analytics': {
                'primary_metrics': ['impressions', 'clicks', 'spend', 'conversions'],
                'chart_types': ['time_series', 'funnel_chart', 'table'],
                'default_filters': {'date_range': 90}
            },
            'audience_insights': {
                'primary_metrics': ['reach', 'frequency', 'impressions'],
                'chart_types': ['demographic_chart', 'geographic_chart', 'table'],
                'default_filters': {'date_range': 30}
            }
        }
        
        return configs.get(job_type_id, {
            'primary_metrics': ['impressions', 'clicks', 'spend'],
            'chart_types': ['time_series', 'bar_chart', 'table'],
            'default_filters': {'date_range': 30}
        })
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, str]]:
        """Get schema information for a table."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = []
                for row in cursor.fetchall():
                    columns.append({
                        'name': row['name'],
                        'type': row['type'],
                        'nullable': not bool(row['notnull']),
                        'primary_key': bool(row['pk'])
                    })
                return columns
        except Exception as e:
            logger.error(f"Failed to get table schema for {table_name}: {e}")
            return []
    
    def generate_dashboard_template(self, job_config: JobTypeConfig) -> str:
        """Generate a complete dashboard template for a job type."""
        table_schema = self.get_table_schema(job_config.table_name)
        
        # Extract column information
        date_columns = [col['name'] for col in table_schema if 'date' in col['name'].lower()]
        numeric_columns = [col['name'] for col in table_schema if col['type'] in ['INTEGER', 'DECIMAL', 'REAL']]
        text_columns = [col['name'] for col in table_schema if col['type'] == 'TEXT']
        
        template = f'''"""
{job_config.job_name} Dashboard
Interactive dashboard for {job_config.description.lower()}.
Auto-generated from template system.
"""

import marimo

__generated_with = "0.9.14"
app = marimo.App(width="full")


@app.cell
def __():
    import marimo as mo
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from utils.db_connection import db_manager
    from utils.common import (
        get_url_param, format_currency, format_number, format_percentage,
        create_error_message, create_info_message
    )
    return (
        mo, pd, px, go, make_subplots, db_manager,
        get_url_param, format_currency, format_number, format_percentage,
        create_error_message, create_info_message
    )


@app.cell
def __(get_url_param, create_error_message):
    # Get account_id from URL parameters and set up error handling
    from utils.error_handler import create_dashboard_error_handler
    
    account_id = get_url_param("account_id")
    error_handler = create_dashboard_error_handler("{job_config.job_name}", account_id)
    
    if not account_id:
        account_error = error_handler.handle_missing_account()
    else:
        account_error = None
    
    return account_id, account_error, error_handler


@app.cell
def __(mo, account_id, account_error):
    # Page header
    if account_error:
        account_error
    else:
        mo.md(f"""
        # 📊 {job_config.job_name}
        
        **Account:** {{account_id}}
        
        {job_config.description}
        """)
    return


@app.cell
def __(mo, account_id):
    # Filters and controls
    if account_id:
        # Date range filter
        date_range_filter = mo.ui.dropdown(
            options={{
                "Last 7 days": "7",
                "Last 30 days": "30", 
                "Last 90 days": "90"
            }},
            value="Last {job_config.default_filters.get('date_range', 30)} days",
            label="Date Range"
        )
        
        # Search filter for campaigns/entities
        search_filter = mo.ui.text(
            placeholder="Search...",
            label="Search Filter"
        )
        
        # Metric selector for charts
        metric_options = {{
{self._generate_metric_options(job_config.primary_metrics)}
        }}
        
        metric_selector = mo.ui.dropdown(
            options=metric_options,
            value="{self._get_metric_label(job_config.primary_metrics[0]) if job_config.primary_metrics else 'Impressions'}",
            label="Primary Metric"
        )
        
        # Display filters
        mo.hstack([date_range_filter, search_filter, metric_selector], justify="start")
    else:
        date_range_filter = search_filter = metric_selector = None
    
    return date_range_filter, search_filter, metric_selector


@app.cell
def __(account_id, date_range_filter, db_manager, error_handler):
    # Load data with error handling
    if account_id and date_range_filter:
        days = int(date_range_filter.value)
        
        def load_data():
            # Query data from the specific table
            query = """
            SELECT *
            FROM {job_config.table_name}
            WHERE account_id = :account_id
            AND {date_columns[0] if date_columns else 'date_start'} >= date('now', '-' || :days || ' days')
            ORDER BY {date_columns[0] if date_columns else 'date_start'} DESC
            """
            return db_manager.query_to_dataframe(query, {{"account_id": account_id, "days": days}})
        
        data = error_handler.safe_execute(load_data, pd.DataFrame(), "Failed to load dashboard data")
        
        if isinstance(data, pd.DataFrame) and data.empty:
            data_message = error_handler.handle_no_data("{job_config.job_type_id}", days)
        else:
            data_message = None
            
            # Validate data quality
            required_columns = {[repr(col) for col in (numeric_columns + text_columns)[:5]]}
            quality_warning = error_handler.validate_data_quality(data, required_columns)
            if quality_warning:
                data_message = quality_warning
    else:
        data = pd.DataFrame()
        data_message = None
    
    return data, data_message


@app.cell
def __(data_message):
    # Show data message if exists
    if data_message:
        data_message
    return


@app.cell
def __(data, search_filter):
    # Apply search filter
    if not data.empty and search_filter and search_filter.value:
        search_term = search_filter.value.lower()
        # Search in text columns
        search_columns = {[repr(col) for col in text_columns[:3]]}  # Limit to first 3 text columns
        
        mask = pd.Series([False] * len(data))
        for col in search_columns:
            if col in data.columns:
                mask |= data[col].astype(str).str.lower().str.contains(search_term, na=False)
        
        filtered_data = data[mask]
    else:
        filtered_data = data
    
    return filtered_data,


@app.cell
def __(mo, filtered_data, format_currency, format_number, format_percentage):
    # Calculate and display KPIs
    if not filtered_data.empty:
        # Calculate metrics based on available columns
        kpi_cards = []
        
{self._generate_kpi_calculations(numeric_columns)}
        
        if kpi_cards:
            kpi_row = mo.hstack(kpi_cards, widths="equal")
            kpi_row
    else:
        kpi_row = None
    
    return kpi_row,


@app.cell
def __(filtered_data, metric_selector, px):
    # Time series chart
    if not filtered_data.empty and metric_selector:
        date_col = "{date_columns[0] if date_columns else 'date_start'}"
        
        if date_col in filtered_data.columns:
            # Aggregate data by date
            daily_data = filtered_data.groupby(date_col).agg({{
{self._generate_aggregation_dict(numeric_columns)}
            }}).reset_index()
            
            # Create time series chart
            selected_metric = metric_selector.value
            
            time_chart = px.line(
                daily_data,
                x=date_col,
                y=selected_metric,
                title=f'{{selected_metric.title()}} Over Time',
                labels={{
                    date_col: 'Date',
                    selected_metric: selected_metric.title()
                }}
            )
            time_chart.update_layout(height=400)
            time_chart.update_traces(line=dict(width=3))
        else:
            time_chart = None
    else:
        time_chart = None
    
    return time_chart,


@app.cell
def __(mo, time_chart, filtered_data):
    # Display charts
    if time_chart:
        return mo.vstack([
            mo.md("## Data Visualization"),
            time_chart
        ])
    elif not filtered_data.empty:
        return mo.vstack([
            mo.md("## Data Overview"),
            mo.md("Time series chart not available - no date column found.")
        ])
    return


@app.cell
def __(mo, filtered_data):
    # Interactive data table
    if not filtered_data.empty:
        # Limit columns for better display
        display_columns = filtered_data.columns[:10].tolist()  # Show first 10 columns
        display_data = filtered_data[display_columns]
        
        # Create interactive table
        data_table = mo.ui.table(
            display_data,
            selection="multi",
            page_size=20,
            show_column_summaries=True
        )
        
        mo.md("## Detailed Data")
        data_table
    else:
        data_table = None
    
    return data_table,


@app.cell
def __(mo, account_id):
    # Navigation and footer
    mo.md(f"""
    ---
    
    ### Navigation
    
    [← Back to Index](/index.py) | [🔄 Refresh Data](/{job_config.job_type_id}_dashboard.py/?account_id={{account_id}})
    
    ### About This Dashboard
    
    This dashboard displays {job_config.description.lower()} for account **{{account_id}}**. 
    Use the filters above to customize the view and explore different time periods.
    
    **Data Source:** `{job_config.table_name}` table
    """)
    return


if __name__ == "__main__":
    app.run()
'''
        
        return template
    
    def _get_metric_label(self, metric: str) -> str:
        """Get formatted label for a metric."""
        label = metric.replace('_', ' ').title()
        if 'spend' in metric.lower() or 'cost' in metric.lower():
            label += " ($)"
        elif 'rate' in metric.lower() or 'ctr' in metric.lower():
            label += " (%)"
        return label

    def _generate_metric_options(self, metrics: List[str]) -> str:
        """Generate metric options for dropdown."""
        options = []
        for metric in metrics:
            label = self._get_metric_label(metric)
            options.append(f'            "{label}": "{metric}"')
        return ',\n'.join(options)
    
    def _generate_kpi_calculations(self, numeric_columns: List[str]) -> str:
        """Generate KPI calculation code."""
        calculations = []
        
        # Common metrics
        common_metrics = ['impressions', 'clicks', 'spend', 'reach', 'conversions']
        
        for metric in common_metrics:
            if metric in numeric_columns:
                if metric == 'spend':
                    calculations.append(f'''        if '{metric}' in filtered_data.columns:
            total_{metric} = filtered_data['{metric}'].sum()
            kpi_cards.append(mo.stat(
                label="Total {metric.title()}",
                value=format_currency(total_{metric}),
                caption="Total cost"
            ))''')
                else:
                    calculations.append(f'''        if '{metric}' in filtered_data.columns:
            total_{metric} = filtered_data['{metric}'].sum()
            kpi_cards.append(mo.stat(
                label="Total {metric.title()}",
                value=format_number(int(total_{metric})),
                caption="{metric.title()} count"
            ))''')
        
        return '\n        \n'.join(calculations) if calculations else '        # No standard metrics found'
    
    def _generate_aggregation_dict(self, numeric_columns: List[str]) -> str:
        """Generate aggregation dictionary for groupby operations."""
        agg_items = []
        for col in numeric_columns[:5]:  # Limit to first 5 numeric columns
            agg_items.append(f"                '{col}': 'sum'")
        return ',\n'.join(agg_items) if agg_items else "                'id': 'count'"
    
    def create_dashboard_notebook(self, job_config: JobTypeConfig, output_dir: Optional[Path] = None) -> Path:
        """Create a dashboard notebook file for a job type."""
        if output_dir is None:
            output_dir = Path(__file__).parent.parent
        
        notebook_filename = f"{job_config.job_type_id}_dashboard.py"
        notebook_path = output_dir / notebook_filename
        
        template_content = self.generate_dashboard_template(job_config)
        
        try:
            with open(notebook_path, 'w') as f:
                f.write(template_content)
            
            logger.info(f"Created dashboard notebook: {notebook_path}")
            return notebook_path
        except Exception as e:
            logger.error(f"Failed to create dashboard notebook: {e}")
            raise
    
    def get_available_dashboards(self) -> List[Dict[str, Any]]:
        """Get list of available dashboard notebooks."""
        job_types = self.discover_job_types()
        dashboards = []
        
        notebooks_dir = Path(__file__).parent.parent
        
        for job_config in job_types:
            notebook_filename = f"{job_config.job_type_id}_dashboard.py"
            notebook_path = notebooks_dir / notebook_filename
            
            dashboards.append({
                'job_type_id': job_config.job_type_id,
                'job_name': job_config.job_name,
                'description': job_config.description,
                'notebook_filename': notebook_filename,
                'notebook_exists': notebook_path.exists(),
                'notebook_path': str(notebook_path)
            })
        
        return dashboards


# Global instance for easy import
template_generator = DashboardTemplateGenerator()