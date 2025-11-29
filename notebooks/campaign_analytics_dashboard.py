"""
Campaign Analytics Dashboard
Interactive dashboard for deep dive campaign performance analysis with conversion tracking.
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
    error_handler = create_dashboard_error_handler("Campaign Analytics", account_id)
    
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
        # 📊 Campaign Analytics
        
        **Account:** {account_id}
        
        Deep dive campaign performance analysis with conversion tracking
        """)
    return


@app.cell
def __(mo, account_id):
    # Filters and controls
    if account_id:
        # Date range filter
        date_range_filter = mo.ui.dropdown(
            options={
                "Last 7 days": "7",
                "Last 30 days": "30", 
                "Last 90 days": "90"
            },
            value="Last 90 days",
            label="Date Range"
        )
        
        # Search filter for campaigns/entities
        search_filter = mo.ui.text(
            placeholder="Search...",
            label="Search Filter"
        )
        
        # Metric selector for charts
        metric_options = {
            "Impressions": "impressions",
            "Clicks": "clicks",
            "Spend ($)": "spend",
            "Conversions": "conversions"
        }
        
        metric_selector = mo.ui.dropdown(
            options=metric_options,
            value="Impressions",
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
            FROM campaign_analytics_data
            WHERE account_id = :account_id
            AND date_start >= date('now', '-' || :days || ' days')
            ORDER BY date_start DESC
            """
            return db_manager.query_to_dataframe(query, {"account_id": account_id, "days": days})
        
        data = error_handler.safe_execute(load_data, pd.DataFrame(), "Failed to load dashboard data")
        
        if isinstance(data, pd.DataFrame) and data.empty:
            data_message = error_handler.handle_no_data("campaign_analytics", days)
        else:
            data_message = None
            
            # Validate data quality
            required_columns = ["'id'", "'impressions'", "'clicks'", "'conversions'", "'account_id'"]
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
        search_columns = ["'account_id'", "'campaign_id'", "'campaign_name'"]  # Limit to first 3 text columns
        
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
        
        if 'impressions' in filtered_data.columns:
            total_impressions = filtered_data['impressions'].sum()
            kpi_cards.append(mo.stat(
                label="Total Impressions",
                value=format_number(int(total_impressions)),
                caption="Impressions count"
            ))
        
        if 'clicks' in filtered_data.columns:
            total_clicks = filtered_data['clicks'].sum()
            kpi_cards.append(mo.stat(
                label="Total Clicks",
                value=format_number(int(total_clicks)),
                caption="Clicks count"
            ))
        
        if 'conversions' in filtered_data.columns:
            total_conversions = filtered_data['conversions'].sum()
            kpi_cards.append(mo.stat(
                label="Total Conversions",
                value=format_number(int(total_conversions)),
                caption="Conversions count"
            ))
        
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
        date_col = "date_start"
        
        if date_col in filtered_data.columns:
            # Aggregate data by date
            daily_data = filtered_data.groupby(date_col).agg({
                'id': 'sum',
                'impressions': 'sum',
                'clicks': 'sum',
                'conversions': 'sum'
            }).reset_index()
            
            # Create time series chart
            selected_metric = metric_selector.value
            
            time_chart = px.line(
                daily_data,
                x=date_col,
                y=selected_metric,
                title=f'{selected_metric.title()} Over Time',
                labels={
                    date_col: 'Date',
                    selected_metric: selected_metric.title()
                }
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
    
    [← Back to Index](/index.py) | [🔄 Refresh Data](/campaign_analytics_dashboard.py/?account_id={account_id})
    
    ### About This Dashboard
    
    This dashboard displays deep dive campaign performance analysis with conversion tracking for account **{account_id}**. 
    Use the filters above to customize the view and explore different time periods.
    
    **Data Source:** `campaign_analytics_data` table
    """)
    return


if __name__ == "__main__":
    app.run()
