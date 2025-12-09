"""
Marimo Ad Performance Dashboard
Interactive dashboard for Meta Ads campaign performance analysis.
"""

import marimo

__generated_with = "0.18.1"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from utils.db_connection import db_manager
    from utils.common import (
        get_url_param,
        format_currency,
        format_number,
        format_percentage,
        create_error_message,
        create_info_message,
    )
    import logging

    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    return (
        create_error_message,
        create_info_message,
        db_manager,
        format_currency,
        format_number,
        format_percentage,
        logger,
        mo,
        pd,
        px,
    )


@app.cell
def _(create_error_message, mo):
    # Get account_id from URL parameters
    account_id = mo.query_params().get("account_id", None)

    if not account_id:
        account_error = create_error_message(
            "Missing Account ID",
            "No account ID specified in the URL.",
            "Please navigate from the index page or add ?account_id=YOUR_ACCOUNT_ID to the URL.",
        )
    else:
        account_error = None

    return account_error, account_id


@app.cell
def _(account_error, account_id, mo):
    # Page header
    if account_error is not None:
        account_error
    else:
        mo.md(
            f"""
        # 📈 Ad Performance Dashboard

        **Account:** {account_id}

        Analyze your Meta Ads campaign performance with interactive visualizations and detailed metrics.
        """
        )
    return


@app.cell
def _(account_id, mo):
    # Filters and controls
    if account_id:
        # Date range filter
        date_range_filter = mo.ui.dropdown(
            options={
                "Last 7 days": "7",
                "Last 30 days": "30",
                "Last 90 days": "90",
            },
            value="Last 30 days",
            label="Date Range",
        )

        # Campaign search filter
        search_filter = mo.ui.text(
            placeholder="Search campaigns...", label="Campaign Search"
        )

        # Metric selector for charts
        metric_selector = mo.ui.dropdown(
            options={
                "Spend ($)": "spend",
                "Impressions": "impressions",
                "Clicks": "clicks",
                "CTR (%)": "ctr",
                "CPC ($)": "cpc",
            },
            value="Spend ($)",
            label="Primary Metric",
        )

        # Display filters
        mo.hstack(
            [date_range_filter, search_filter, metric_selector], justify="start"
        )
    else:
        date_range_filter = None
        search_filter = None
        metric_selector = None

    return date_range_filter, metric_selector, search_filter


@app.cell
def _(account_id, create_info_message, date_range_filter, db_manager, logger, pd):
    # Load ad performance data
    if (
        account_id
        and date_range_filter is not None
        and date_range_filter.value is not None
    ):
        days = int(date_range_filter.value)
        logger.info(
            f"Fetching ad performance data for account {account_id} for last {days} days"
        )

        ad_data = db_manager.get_ad_performance_data(account_id, days)
        logger.info(f"Retrieved {len(ad_data)} rows of ad data")

        if ad_data.empty:
            data_message = create_info_message(
                "No Data Available",
                f"No ad performance data found for account {account_id} in the last {days} days.",
            )
            logger.warning(
                f"No ad data found for account {account_id} in last {days} days"
            )
        else:
            data_message = None
            logger.info(
                f"Successfully loaded {len(ad_data)} rows with columns: {list(ad_data.columns)}"
            )
    else:
        ad_data = pd.DataFrame()
        data_message = None
        logger.warning("Skipping data load - missing account_id or date_range_filter")

    return ad_data, data_message


@app.cell
def _(data_message, mo):
    # Show data message if exists
    if data_message is not None:
        data_message
    else:
        # Show a subtle indicator that data loaded successfully
        mo.callout(
            mo.md("✅ Data loaded successfully"),
            kind="success"
        )
    return


@app.cell
def _(ad_data, logger, search_filter):
    # Apply search filter
    if (
        not ad_data.empty
        and search_filter is not None
        and (
            search_filter.value is not None and search_filter.value.strip() != ""
        )
    ):
        search_term = search_filter.value.lower()
        filtered_data = ad_data[
            ad_data["campaign_name"]
            .str.lower()
            .str.contains(search_term, na=False)
        ]
        logger.info(
            f"Applied search filter '{search_term}': {len(filtered_data)} rows match"
        )
    else:
        filtered_data = ad_data
        if not ad_data.empty:
            logger.info(f"No search filter applied, showing all {len(filtered_data)} rows")

    return (filtered_data,)


@app.cell
def _(filtered_data, format_currency, format_number, format_percentage, mo):
    # Calculate and display KPIs
    if not filtered_data.empty:
        # Calculate totals
        total_impressions = filtered_data["impressions"].sum()
        total_clicks = filtered_data["clicks"].sum()
        total_spend = filtered_data["spend"].sum()
        total_reach = filtered_data["reach"].sum()

        # Calculate averages
        avg_ctr = (
            total_clicks / total_impressions * 100
            if total_impressions > 0
            else 0
        )
        avg_cpc = total_spend / total_clicks if total_clicks > 0 else 0
        avg_cpm = (
            total_spend / total_impressions * 1000
            if total_impressions > 0
            else 0
        )
        avg_frequency = filtered_data["frequency"].mean()

        # Create KPI cards
        kpi_row = mo.hstack(
            [
                mo.stat(
                    label="Total Impressions",
                    value=format_number(int(total_impressions)),
                    caption="Ad views",
                ),
                mo.stat(
                    label="Total Clicks",
                    value=format_number(int(total_clicks)),
                    caption=f"CTR: {format_percentage(avg_ctr)}",
                ),
                mo.stat(
                    label="Total Spend",
                    value=format_currency(total_spend),
                    caption=f"CPC: {format_currency(avg_cpc)}",
                ),
                mo.stat(
                    label="Total Reach",
                    value=format_number(int(total_reach)),
                    caption=f"Frequency: {avg_frequency:.2f}",
                ),
                mo.stat(
                    label="CPM",
                    value=format_currency(avg_cpm),
                    caption="Cost per 1K impressions",
                ),
            ],
            widths="equal",
        )

        kpi_row
    else:
        # Show empty state for KPIs
        mo.callout(
            mo.md(
                """
                ### 📊 No Metrics Available
                
                There is no data to display KPIs. This could be because:
                - No ad campaigns ran during the selected time period
                - Your search filter excluded all campaigns
                - The data hasn't been synced yet
                """
            ),
            kind="info",
        )
    return


@app.cell
def _(filtered_data, metric_selector, px, mo):
    # Time series chart
    if (
        not filtered_data.empty
        and metric_selector is not None
        and metric_selector.value is not None
    ):
        # Aggregate data by date
        daily_data = (
            filtered_data.groupby("date_start")
            .agg(
                {
                    "impressions": "sum",
                    "clicks": "sum",
                    "spend": "sum",
                    "reach": "sum",
                }
            )
            .reset_index()
        )

        # Calculate derived metrics
        daily_data["ctr"] = (
            daily_data["clicks"] / daily_data["impressions"] * 100
        ).fillna(0)
        daily_data["cpc"] = (
            daily_data["spend"] / daily_data["clicks"]
        ).fillna(0)
        daily_data["cpm"] = (
            daily_data["spend"] / daily_data["impressions"] * 1000
        ).fillna(0)

        # Create time series chart
        selected_metric = metric_selector.value
        metric_labels = {
            "spend": "Spend ($)",
            "impressions": "Impressions",
            "clicks": "Clicks",
            "ctr": "CTR (%)",
            "cpc": "CPC ($)",
        }

        time_chart = px.line(
            daily_data,
            x="date_start",
            y=selected_metric,
            title=f"{metric_labels[selected_metric]} Over Time",
            labels={
                "date_start": "Date",
                selected_metric: metric_labels[selected_metric],
            },
        )
        time_chart.update_layout(height=400)
        time_chart.update_traces(line=dict(width=3))

    else:
        time_chart = mo.callout(
            mo.md(
                """
                ### 📈 No Trend Data
                
                Cannot display time series chart - no data available for the selected filters.
                """
            ),
            kind="warn",
        )

    return (time_chart,)


@app.cell
def _(filtered_data, px, mo):
    # Campaign performance bar chart
    if not filtered_data.empty:
        # Aggregate by campaign
        campaign_data = (
            filtered_data.groupby("campaign_name")
            .agg(
                {
                    "impressions": "sum",
                    "clicks": "sum",
                    "spend": "sum",
                }
            )
            .reset_index()
        )

        # Calculate CTR and CPC
        campaign_data["ctr"] = (
            campaign_data["clicks"] / campaign_data["impressions"] * 100
        ).fillna(0)
        campaign_data["cpc"] = (
            campaign_data["spend"] / campaign_data["clicks"]
        ).fillna(0)

        # Sort by spend and take top 10
        campaign_data = campaign_data.sort_values(
            "spend", ascending=False
        ).head(10)

        # Create bar chart
        campaign_chart = px.bar(
            campaign_data,
            x="campaign_name",
            y="spend",
            title="Top 10 Campaigns by Spend",
            labels={
                "campaign_name": "Campaign",
                "spend": "Spend ($)",
            },
            hover_data=["clicks", "impressions", "ctr", "cpc"],
        )
        campaign_chart.update_layout(height=400)
        campaign_chart.update_xaxes(tickangle=45)

    else:
        campaign_chart = mo.callout(
            mo.md(
                """
                ### 📊 No Campaign Data
                
                Cannot display campaign performance - no data available.
                """
            ),
            kind="warn",
        )

    return (campaign_chart,)


@app.cell
def _(filtered_data, px, mo):
    # Performance scatter plot
    if not filtered_data.empty:
        # Aggregate by ad set for scatter plot
        adset_data = (
            filtered_data.groupby(["campaign_name", "adset_name"])
            .agg(
                {
                    "impressions": "sum",
                    "clicks": "sum",
                    "spend": "sum",
                }
            )
            .reset_index()
        )

        # Calculate metrics
        adset_data["ctr"] = (
            adset_data["clicks"] / adset_data["impressions"] * 100
        ).fillna(0)
        adset_data["cpc"] = (
            adset_data["spend"] / adset_data["clicks"]
        ).fillna(0)

        # Create scatter plot
        scatter_chart = px.scatter(
            adset_data,
            x="cpc",
            y="ctr",
            size="spend",
            color="campaign_name",
            hover_name="adset_name",
            title="Ad Set Performance: CTR vs CPC",
            labels={
                "cpc": "Cost Per Click ($)",
                "ctr": "Click-Through Rate (%)",
                "campaign_name": "Campaign",
            },
        )
        scatter_chart.update_layout(height=400)

    else:
        scatter_chart = mo.callout(
            mo.md(
                """
                ### 🎯 No Performance Data
                
                Cannot display ad set performance scatter plot - no data available.
                """
            ),
            kind="warn",
        )

    return (scatter_chart,)


@app.cell
def _(campaign_chart, mo, scatter_chart, time_chart):
    # Display charts in tabs
    _chart_tabs = mo.ui.tabs(
        {
            "📈 Trends": time_chart,
            "📊 Campaigns": campaign_chart,
            "🎯 Performance": scatter_chart,
        }
    )

    _chart_tabs
    return


@app.cell
def _(
    filtered_data,
    format_currency,
    format_number,
    format_percentage,
    mo,
    pd,
):
    # Interactive data table
    if not filtered_data.empty:
        # Prepare data for table display
        table_data = filtered_data.copy()

        # Format columns for better display
        table_data["spend_formatted"] = table_data["spend"].apply(
            format_currency
        )
        table_data["impressions_formatted"] = table_data[
            "impressions"
        ].apply(format_number)
        table_data["clicks_formatted"] = table_data["clicks"].apply(
            format_number
        )
        table_data["ctr_formatted"] = table_data["ctr"].apply(
            lambda x: format_percentage(x) if pd.notna(x) else "0.00%"
        )
        table_data["cpc_formatted"] = table_data["cpc"].apply(
            lambda x: format_currency(x) if pd.notna(x) else "$0.00"
        )

        # Select and reorder columns for display
        display_columns = [
            "date_start",
            "campaign_name",
            "adset_name",
            "ad_name",
            "impressions_formatted",
            "clicks_formatted",
            "spend_formatted",
            "ctr_formatted",
            "cpc_formatted",
        ]

        display_data = table_data[display_columns].rename(
            columns={
                "date_start": "Date",
                "campaign_name": "Campaign",
                "adset_name": "Ad Set",
                "ad_name": "Ad",
                "impressions_formatted": "Impressions",
                "clicks_formatted": "Clicks",
                "spend_formatted": "Spend",
                "ctr_formatted": "CTR",
                "cpc_formatted": "CPC",
            }
        )

        # Create interactive table
        data_table = mo.ui.table(
            display_data,
            selection="multi",
            page_size=20,
            show_column_summaries=True,
        )

        mo.md("## Detailed Data")
        data_table
    else:
        mo.md("## Detailed Data")
        mo.callout(
            mo.md(
                """
                ### 📋 No Detailed Data Available
                
                The data table is empty because:
                - No campaigns match your current filters
                - No ad performance data exists for the selected date range
                - Try adjusting the date range or clearing the search filter
                """
            ),
            kind="info",
        )
    return


@app.cell
def _(account_id, mo):
    # Navigation and footer
    mo.md(
        f"""
    ---

    ### Navigation

    [← Back to Index](/) | [🔄 Refresh Data](/ad_performance_dashboard/?account_id={account_id})

    ### About This Dashboard

    This dashboard displays Meta Ads performance data for account **{account_id}**. 
    Use the filters above to customize the view and explore different time periods and campaigns.

    **Features:**
    - Interactive time series charts
    - Campaign performance comparisons  
    - Detailed data table with sorting and filtering
    - Real-time KPI calculations
    """
    )
    return


if __name__ == "__main__":
    app.run()
