"""
Audience Insights Dashboard
Interactive dashboard for demographic and behavioral analysis of target audiences.
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
        format_currency, format_number, format_percentage,
        create_error_message, create_info_message
    )
    return (
        mo, pd, px, go, make_subplots, db_manager,
        format_currency, format_number, format_percentage,
        create_error_message, create_info_message
    )


@app.cell
def __(create_error_message, mo):
    # Get account_id from URL parameters
    query_params = mo.query_params()
    account_id = query_params.get("account_id", None)
    
    if not account_id:
        account_error = create_error_message(
            "Missing Account ID",
            "No account ID specified in the URL.",
            "Please navigate from the index page or add ?account_id=YOUR_ACCOUNT_ID to the URL.",
        )
    else:
        account_error = None
    
    return account_id, account_error, query_params


@app.cell
def __(mo, account_id, account_error):
    # Page header
    if account_error:
        _header_display = account_error
    else:
        _header_display = mo.md(f"""
        # 📊 Audience Insights
        
        **Account:** {account_id}
        
        Demographic and behavioral analysis of target audiences
        """)
    
    _header_display


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
            value="Last 30 days",
            label="Date Range"
        )
        
        # Search filter for campaigns/entities
        search_filter = mo.ui.text(
            placeholder="Search...",
            label="Search Filter"
        )
        
        # Metric selector for charts (only showing columns that exist in the data)
        metric_options = {
            "Reach": "reach",
            "Impressions": "impressions"
        }
        
        metric_selector = mo.ui.dropdown(
            options=metric_options,
            value="Reach",
            label="Primary Metric"
        )
        
        # Display filters
        _filters_display = mo.hstack([date_range_filter, search_filter, metric_selector], justify="start")
    else:
        date_range_filter = search_filter = metric_selector = None
        _filters_display = None
    
    _filters_display
    return date_range_filter, search_filter, metric_selector


@app.cell
def __(account_id, create_info_message, date_range_filter, db_manager, pd):
    # Load data
    if account_id and date_range_filter:
        days = int(date_range_filter.value)
        
        # Query data from the specific table
        query = """
        SELECT *
        FROM audience_insights_data
        WHERE account_id = :account_id
        AND date_start >= date('now', '-' || :days || ' days')
        ORDER BY date_start DESC
        """
        data = db_manager.query_to_dataframe(query, {"account_id": account_id, "days": days})
        
        if data.empty:
            data_message = create_info_message(
                "No Data Available",
                f"No audience insights data found for account {account_id} in the last {days} days. "
                "Data may not have been extracted yet or the account may not have any activity."
            )
        else:
            data_message = None
    else:
        data = pd.DataFrame()
        data_message = None
    
    return data, data_message


@app.cell
def __(data_message):
    # Show data message if exists
    if data_message:
        _data_message_display = data_message
    else:
        _data_message_display = None
    
    _data_message_display


@app.cell
def __(data, search_filter):
    # Apply search filter
    if not data.empty and search_filter and search_filter.value:
        search_term = search_filter.value.lower()
        # Search in text columns
        search_columns = ["'account_id'", "'age_range'", "'gender'"]  # Limit to first 3 text columns
        
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
        
        if 'reach' in filtered_data.columns:
            total_reach = filtered_data['reach'].sum()
            kpi_cards.append(mo.stat(
                label="Total Reach",
                value=format_number(int(total_reach)),
                caption="Reach count"
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
                'reach': 'sum'
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
        _charts_display = mo.vstack([
            mo.md("## Data Visualization"),
            time_chart
        ])
    elif not filtered_data.empty:
        _charts_display = mo.vstack([
            mo.md("## Data Overview"),
            mo.md("Time series chart not available - no date column found.")
        ])
    else:
        _charts_display = None
    
    _charts_display


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
        
        _table_display = mo.vstack([
            mo.md("## Detailed Data"),
            data_table
        ])
    else:
        _table_display = None
    
    _table_display
    
    return data_table,


@app.cell
def __(mo, account_id):
    # Navigation and footer
    mo.md(f"""
    ---
    
    ### Navigation
    
    [← Back to Index](/) | [🔄 Refresh Data](/audience_insights_dashboard/?account_id={account_id})
    
    ### About This Dashboard
    
    This dashboard displays demographic and behavioral analysis of target audiences for account **{account_id}**. 
    Use the filters above to customize the view and explore different time periods.
    
    **Data Source:** `audience_insights_data` table
    """)
    return


if __name__ == "__main__":
    app.run()
