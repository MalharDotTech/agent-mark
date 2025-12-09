"""
Marimo Reach & Frequency Dashboard
Interactive dashboard for Meta Ads reach and frequency analysis with audience overlap detection.
"""

import marimo

__generated_with = "0.18.1"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    import plotly.express as px
    from utils.db_connection import db_manager
    from utils.common import (
        format_currency,
        format_number,
        format_percentage,
        create_error_message,
        create_info_message,
        create_warning_message,
    )
    import logging

    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    return (
        create_error_message,
        create_info_message,
        create_warning_message,
        db_manager,
        format_currency,
        format_number,
        format_percentage,
        go,
        logger,
        mo,
        np,
        pd,
        px,
    )


@app.cell
def _(create_error_message, mo):
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

    return account_error, account_id, query_params


@app.cell
def _(account_error, account_id, mo):
    # Page header
    if account_error is not None:
        _header_display = account_error
    else:
        _header_display = mo.md(
            f"""
        # 📡 Reach & Frequency Dashboard

        **Account:** {account_id}

        Analyze cumulative reach and frequency trends, and identify audience overlap between campaigns and ad sets.
        """
        )
    
    _header_display
    return


@app.cell
def _(account_id, mo):
    # Dashboard mode selector and filters
    if account_id:
        # Analysis mode selector
        dashboard_mode = mo.ui.dropdown(
            options={
                "Cumulative Reach & Frequency": "cumulative",
                "Audience Overlap Analysis": "overlap",
            },
            value="Cumulative Reach & Frequency",
            label="Select Analysis Type",
        )

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

        # Display filters
        _filters_display = mo.hstack([dashboard_mode, date_range_filter], justify="start")
    else:
        dashboard_mode = None
        date_range_filter = None
        _filters_display = mo.md("")
    
    _filters_display
    return dashboard_mode, date_range_filter


@app.cell
def _(account_id, date_range_filter, db_manager, logger, pd):
    # Load RNF cumulative data
    if account_id and date_range_filter is not None and date_range_filter.value is not None:
        _days_cumulative = int(date_range_filter.value)
        logger.info(
            f"Fetching RNF cumulative data for account {account_id} for last {_days_cumulative} days"
        )

        cumulative_data = db_manager.get_rnf_cumulative_data(account_id, _days_cumulative)
        logger.info(f"Retrieved {len(cumulative_data)} rows of cumulative data")
    else:
        cumulative_data = pd.DataFrame()
        logger.warning("Skipping cumulative data load - missing parameters")

    return (cumulative_data,)


@app.cell
def _(account_id, date_range_filter, db_manager, logger, pd):
    # Load RNF overlap data
    if account_id and date_range_filter is not None and date_range_filter.value is not None:
        _days_overlap = int(date_range_filter.value)
        logger.info(
            f"Fetching RNF overlap data for account {account_id} for last {_days_overlap} days"
        )

        overlap_data = db_manager.get_rnf_overlap_data(account_id, _days_overlap)
        logger.info(f"Retrieved {len(overlap_data)} rows of overlap data")
    else:
        overlap_data = pd.DataFrame()
        logger.warning("Skipping overlap data load - missing parameters")

    return (overlap_data,)


@app.cell
def _(create_info_message, cumulative_data, dashboard_mode, mo):
    # Show data status for cumulative mode
    if dashboard_mode is not None and dashboard_mode.value == "cumulative":
        if cumulative_data.empty:
            _cumulative_status_display = create_info_message(
                "No Data Available",
                "No cumulative reach and frequency data found for this account and date range.",
            )
        else:
            _cumulative_status_display = mo.callout(
                mo.md(f"✅ Loaded {len(cumulative_data)} cumulative data records"),
                kind="success",
            )
    else:
        _cumulative_status_display = mo.md("")
    
    _cumulative_status_display
    return


@app.cell
def _(create_info_message, dashboard_mode, mo, overlap_data):
    # Show data status for overlap mode
    if dashboard_mode is not None and dashboard_mode.value == "overlap":
        if overlap_data.empty:
            _overlap_status_display = create_info_message(
                "No Data Available",
                "No audience overlap data found for this account and date range.",
            )
        else:
            _overlap_status_display = mo.callout(
                mo.md(f"✅ Loaded {len(overlap_data)} overlap data records"),
                kind="success",
            )
    else:
        _overlap_status_display = mo.md("")
    
    _overlap_status_display
    return


@app.cell
def _(cumulative_data, dashboard_mode, format_currency, format_number, mo):
    # Cumulative Analysis - Key Metrics
    if (
        dashboard_mode is not None
        and dashboard_mode.value == "cumulative"
        and not cumulative_data.empty
    ):
        # Get the latest cumulative values
        latest_data = cumulative_data.iloc[-1]

        final_reach = int(latest_data.get("reach", 0))
        final_frequency = float(latest_data.get("frequency", 0))
        total_spend = float(latest_data.get("spend", 0))
        total_impressions = int(latest_data.get("impressions", 0))

        # Create KPI cards
        _cumulative_kpis_display = mo.vstack([
            mo.md("## Key Metrics Summary"),
            mo.hstack(
                [
                    mo.stat(
                        label="Total Reach",
                        value=format_number(final_reach),
                        caption="Unique users reached",
                    ),
                    mo.stat(
                        label="Average Frequency",
                        value=f"{final_frequency:.2f}",
                        caption="Avg impressions per user",
                    ),
                    mo.stat(
                        label="Total Spend",
                        value=format_currency(total_spend),
                        caption="Campaign investment",
                    ),
                    mo.stat(
                        label="Total Impressions",
                        value=format_number(total_impressions),
                        caption="Ad views",
                    ),
                ],
                justify="start",
            ),
        ])
    else:
        _cumulative_kpis_display = mo.md("")
    
    _cumulative_kpis_display
    return


@app.cell
def _(cumulative_data, dashboard_mode, go, mo):
    # Cumulative Analysis - Reach & Frequency Chart
    if (
        dashboard_mode is not None
        and dashboard_mode.value == "cumulative"
        and not cumulative_data.empty
    ):
        # Create dual-axis chart
        fig_cumulative = go.Figure()

        # Add Reach line
        fig_cumulative.add_trace(
            go.Scatter(
                x=cumulative_data["date_start"],
                y=cumulative_data["reach"],
                name="Cumulative Reach",
                mode="lines+markers",
                line=dict(color="blue", width=2),
                yaxis="y",
            )
        )

        # Add Frequency line
        fig_cumulative.add_trace(
            go.Scatter(
                x=cumulative_data["date_start"],
                y=cumulative_data["frequency"],
                name="Average Frequency",
                mode="lines+markers",
                line=dict(color="red", width=2),
                yaxis="y2",
            )
        )

        fig_cumulative.update_layout(
            title="Cumulative Reach & Frequency Over Time",
            xaxis_title="Date",
            yaxis=dict(title="Reach", side="left"),
            yaxis2=dict(title="Frequency", overlaying="y", side="right"),
            hovermode="x unified",
            height=400,
            showlegend=True,
        )

        _cumulative_chart_display = mo.vstack([
            mo.md("## Cumulative Trends"),
            mo.ui.plotly(fig_cumulative)
        ])
    else:
        _cumulative_chart_display = mo.md("")
    
    _cumulative_chart_display
    return (fig_cumulative,)


@app.cell
def _(cumulative_data, dashboard_mode, go, mo):
    # Cumulative Analysis - Spend Chart
    if (
        dashboard_mode is not None
        and dashboard_mode.value == "cumulative"
        and not cumulative_data.empty
    ):
        # Create spend bar chart
        fig_spend = go.Figure()
        fig_spend.add_trace(
            go.Bar(
                x=cumulative_data["date_start"],
                y=cumulative_data["spend"],
                name="Cumulative Spend",
                marker_color="green",
            )
        )
        fig_spend.update_layout(
            title="Cumulative Spend",
            xaxis_title="Date",
            yaxis_title="Spend ($)",
            height=350,
        )

        # Create CTR chart
        fig_ctr = go.Figure()
        fig_ctr.add_trace(
            go.Scatter(
                x=cumulative_data["date_start"],
                y=cumulative_data["ctr"],
                name="CTR",
                mode="lines+markers",
                line=dict(color="orange", width=2),
            )
        )
        fig_ctr.update_layout(
            title="Click-Through Rate Trend",
            xaxis_title="Date",
            yaxis_title="CTR (%)",
            height=350,
        )

        # Display side by side
        # Use vstack for better responsive layout (prevents horizontal scrolling)
        _cumulative_charts_display = mo.vstack(
            [mo.ui.plotly(fig_spend), mo.ui.plotly(fig_ctr)],
        )
    else:
        fig_spend = None
        fig_ctr = None
        _cumulative_charts_display = mo.md("")
    
    _cumulative_charts_display
    return fig_ctr, fig_spend


@app.cell
def _(cumulative_data, dashboard_mode, mo):
    # Cumulative Analysis - Data Table
    if (
        dashboard_mode is not None
        and dashboard_mode.value == "cumulative"
        and not cumulative_data.empty
    ):
        # Format the dataframe for display
        display_cumulative = cumulative_data.copy()
        
        # Select relevant columns
        columns_to_display = [
            "date_start",
            "reach",
            "frequency",
            "impressions",
            "spend",
            "clicks",
            "cpm",
            "cpp",
            "ctr",
        ]
        
        # Filter to columns that exist
        existing_columns = [col for col in columns_to_display if col in display_cumulative.columns]
        display_cumulative = display_cumulative[existing_columns]

        _cumulative_table_display = mo.vstack([
            mo.md("## Detailed Data"),
            mo.ui.table(
                display_cumulative,
                selection=None,
                pagination=True,
                page_size=10,
            )
        ])
    else:
        display_cumulative = None
        _cumulative_table_display = mo.md("")
    
    _cumulative_table_display
    return (display_cumulative,)


@app.cell
def _(dashboard_mode, format_number, mo, overlap_data):
    # Overlap Analysis - Summary Metrics
    if (
        dashboard_mode is not None
        and dashboard_mode.value == "overlap"
        and not overlap_data.empty
    ):
        total_pairs = len(overlap_data)
        avg_overlap_pct = overlap_data["overlap_percentage"].mean()
        high_overlap_count = len(overlap_data[overlap_data["overlap_percentage"] > 30])

        _overlap_kpis_display = mo.vstack([
            mo.md("## Overlap Summary"),
            mo.hstack(
                [
                    mo.stat(
                        label="Total Pairs Analyzed",
                        value=format_number(total_pairs),
                        caption="Campaign/AdSet pairs",
                    ),
                    mo.stat(
                        label="Average Overlap",
                        value=f"{avg_overlap_pct:.1f}%",
                        caption="Across all pairs",
                    ),
                    mo.stat(
                        label="High Overlap Pairs",
                        value=format_number(high_overlap_count),
                        caption=">30% overlap",
                    ),
                ],
                justify="start",
            ),
        ])
    else:
        total_pairs = 0
        avg_overlap_pct = 0
        high_overlap_count = 0
        _overlap_kpis_display = mo.md("")
    
    _overlap_kpis_display
    return avg_overlap_pct, high_overlap_count, total_pairs


@app.cell
def _(dashboard_mode, go, mo, np, overlap_data):
    # Overlap Analysis - Heatmap
    if (
        dashboard_mode is not None
        and dashboard_mode.value == "overlap"
        and not overlap_data.empty
    ):
        # Get unique entity names
        entity1_names = overlap_data["entity1_name"].unique().tolist()
        entity2_names = overlap_data["entity2_name"].unique().tolist()
        all_entities = sorted(list(set(entity1_names + entity2_names)))

        # Create overlap matrix
        matrix_size = len(all_entities)
        overlap_matrix = np.zeros((matrix_size, matrix_size))

        for _, row in overlap_data.iterrows():
            try:
                idx1 = all_entities.index(row["entity1_name"])
                idx2 = all_entities.index(row["entity2_name"])
                overlap_pct = row["overlap_percentage"]
                overlap_matrix[idx1, idx2] = overlap_pct
                overlap_matrix[idx2, idx1] = overlap_pct
            except ValueError:
                continue

        # Create heatmap
        fig_heatmap = go.Figure(
            data=go.Heatmap(
                z=overlap_matrix,
                x=all_entities,
                y=all_entities,
                colorscale="RdYlBu_r",
                text=[[f"{val:.1f}%" for val in row] for row in overlap_matrix],
                texttemplate="%{text}",
                textfont={"size": 10},
                colorbar=dict(title="Overlap %"),
            )
        )

        fig_heatmap.update_layout(
            title="Audience Overlap Heatmap",
            height=500,
            xaxis_title="",
            yaxis_title="",
        )

        _heatmap_display = mo.vstack([
            mo.md("## Audience Overlap Heatmap"),
            mo.ui.plotly(fig_heatmap)
        ])
    else:
        all_entities = []
        entity1_names = []
        entity2_names = []
        fig_heatmap = None
        matrix_size = 0
        overlap_matrix = None
        _heatmap_display = mo.md("")
    
    _heatmap_display
    return all_entities, entity1_names, entity2_names, fig_heatmap, matrix_size, overlap_matrix


@app.cell
def _(dashboard_mode, mo, overlap_data):
    # Overlap Analysis - Top 10 Overlapping Pairs
    if (
        dashboard_mode is not None
        and dashboard_mode.value == "overlap"
        and not overlap_data.empty
    ):
        # Get top 10 by overlap percentage
        top_overlaps = overlap_data.nlargest(10, "overlap_percentage")

        # Select relevant columns for display
        display_overlap = top_overlaps[
            [
                "entity1_name",
                "entity2_name",
                "reach1",
                "reach2",
                "combined_reach",
                "overlap_count",
                "overlap_percentage",
            ]
        ].copy()

        # Rename columns for better display
        display_overlap.columns = [
            "Item 1",
            "Item 2",
            "Reach 1",
            "Reach 2",
            "Combined Reach",
            "Overlap Count",
            "Overlap %",
        ]

        _overlap_table_display = mo.vstack([
            mo.md("## Top 10 Overlapping Pairs"),
            mo.ui.table(
                display_overlap,
                selection=None,
                pagination=False,
            )
        ])
    else:
        display_overlap = None
        top_overlaps = None
        _overlap_table_display = mo.md("")
    
    _overlap_table_display
    return display_overlap, top_overlaps


@app.cell
def _(create_warning_message, dashboard_mode, mo, overlap_data, pd):
    # Overlap Analysis - Recommendations
    if (
        dashboard_mode is not None
        and dashboard_mode.value == "overlap"
        and not overlap_data.empty
    ):
        high_overlap_pairs = overlap_data[overlap_data["overlap_percentage"] > 30]

        if not high_overlap_pairs.empty:
            # Build warning message with pairs
            pairs_list = []
            for _, pair in high_overlap_pairs.iterrows():
                pairs_list.append(
                    f"• **{pair['entity1_name']}** and **{pair['entity2_name']}**: {pair['overlap_percentage']:.1f}% overlap"
                )
            
            pairs_text = "\n".join(pairs_list[:5])  # Show top 5
            
            _recommendations_display = mo.vstack([
                mo.md("## 📊 Recommendations"),
                create_warning_message(
                    f"High Overlap Detected",
                    f"Found {len(high_overlap_pairs)} pairs with >30% overlap",
                ),
                mo.md(f"""
                {pairs_text}

                **Suggested Actions:**
                1. Consider consolidating highly overlapping campaigns/ad sets
                2. Use audience exclusions to prevent overlap
                3. Differentiate targeting criteria or creative strategies
                4. Adjust budgets to avoid competitive bidding
                """),
            ])
        else:
            _recommendations_display = mo.vstack([
                mo.md("## 📊 Recommendations"),
                mo.callout(
                    mo.md("✅ All overlap percentages are within acceptable range (<30%)"),
                    kind="success",
                )
            ])
    else:
        high_overlap_pairs = pd.DataFrame()
        pairs_list = []
        pairs_text = ""
        _recommendations_display = mo.md("")
    
    _recommendations_display
    return high_overlap_pairs, pairs_list, pairs_text


@app.cell
def _(mo):
    # Footer
    mo.md("""
    ---
    
    ### About This Dashboard
    
    **Cumulative Reach & Frequency:** Track how reach and frequency build up over time. 
    Cumulative reach shows unique users reached, while frequency indicates average impressions per user.
    
    **Audience Overlap Analysis:** Identify audiences that are targeted by multiple campaigns or ad sets.
    High overlap (>30%) may indicate inefficient targeting or competitive bidding within your account.
    
    💡 **Tip:** Navigate back to the index page to view other dashboards or switch accounts.
    """)
    return


if __name__ == "__main__":
    app.run()
