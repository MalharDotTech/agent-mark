"""
Marimo Index Notebook - Account Selection and Navigation
Main entry point for the Meta Ads Analytics Dashboard system.
"""

import marimo

__generated_with = "0.17.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    from utils.db_connection import db_manager
    from utils.common import create_dashboard_card, create_error_message, create_info_message
    return (
        create_dashboard_card,
        create_error_message,
        create_info_message,
        db_manager,
        mo,
        pd,
    )


@app.cell
def _(mo):
    # Page header - MUST be last expression to display
    mo.md("""
    # 📊 Meta Ads Analytics Dashboard

    Welcome to your centralized analytics platform. Select an account below to access your dashboards.

    **Status:** Loading accounts and dashboards...
    """)
    return


@app.cell
def _(create_error_message, db_manager, pd):
    # Test database connection and load accounts
    connection_test = db_manager.test_connection()

    if not connection_test:
        connection_error = create_error_message(
            "Database Connection Failed",
            "Unable to connect to the SQLite database.",
            "Please ensure the database has been initialized and is accessible."
        )
        accounts_df = pd.DataFrame()
    else:
        connection_error = None
        try:
            accounts_df = db_manager.get_accounts()
            print(f"Loaded {len(accounts_df)} accounts from database")
        except Exception as e:
            print(f"Error loading accounts: {e}")
            accounts_df = pd.DataFrame()
    return accounts_df, connection_error


@app.cell
def _(accounts_df, connection_error, mo):
    # Show connection error or header - MUST output something
    if connection_error:
        _display_header = connection_error
    elif not accounts_df.empty:
        _display_header = mo.md("## Select Account")
    else:
        _display_header = mo.md("")

    _display_header
    return


@app.cell
def _(accounts_df, mo):
    # Always define account_selector
    if not accounts_df.empty:
        account_options = {
            row['account_name']: row['account_id']
            for _, row in accounts_df.iterrows()
        }
        default_value = list(account_options.keys())[0] if account_options else ""
    else:
        account_options = {"": "No accounts available"}
        default_value = ""

    account_selector = mo.ui.dropdown(
        options=account_options,
        value=default_value,
        label="Choose an account to view dashboards",
    )
    return account_options, account_selector


@app.cell
def _(account_options, account_selector, accounts_df, create_info_message, mo):
    # Display selector or info message - MUST be last expression
    if not accounts_df.empty:
        _account_selector_display = mo.vstack([
            mo.md(f"**{len(account_options)} accounts available**"),
            account_selector
        ])
    else:
        _account_selector_display = create_info_message(
            "No Accounts Found",
            "No Meta Ads accounts are currently available. Please run data extraction first."
        )

    _account_selector_display
    return


@app.cell
def _(account_selector, db_manager, pd):
    # Get job types for selected account
    if account_selector.value and account_selector.value != "":
        selected_account_id = account_selector.value
        print(selected_account_id)
        job_types_df = db_manager.get_job_types_for_account(selected_account_id)
    else:
        selected_account_id = None
        job_types_df = pd.DataFrame()
    return job_types_df, selected_account_id


@app.cell
def _(
    create_dashboard_card,
    create_info_message,
    job_types_df,
    mo,
    selected_account_id,
):
    # Display available dashboards - MUST output at end
    from utils.dashboard_factory import dashboard_factory

    if selected_account_id:
        # Get dashboard registry
        dashboard_registry = dashboard_factory.get_dashboard_registry()

        # Create dashboard cards
        dashboard_cards = []

        for dashboard in dashboard_registry:
            job_type = dashboard['job_type_id']
            job_name = dashboard['job_name']
            description = dashboard['description']
            notebook_exists = dashboard['notebook_exists']

            # Check if this job type has data
            job_has_data = False
            record_count = 0
            last_updated = "Never"

            if not job_types_df.empty:
                matching_jobs = job_types_df[job_types_df['job_type'] == job_type]
                if not matching_jobs.empty:
                    job_has_data = True
                    record_count = matching_jobs.iloc[0]['record_count']
                    last_updated = str(matching_jobs.iloc[0]['last_updated'])[:19] if matching_jobs.iloc[0]['last_updated'] else "Never"

            # Dashboard configuration
            dashboard_config = {
                'ad_performance': {
                    'icon': '📈',
                    'title': 'Ad Performance Dashboard',
                    'enhanced_description': 'Campaign performance metrics, spend analysis, and key performance indicators'
                },
                'campaign_analytics': {
                    'icon': '📊',
                    'title': 'Campaign Analytics Dashboard', 
                    'enhanced_description': 'Deep dive campaign analysis with conversion tracking and ROAS metrics'
                },
                'audience_insights': {
                    'icon': '👥',
                    'title': 'Audience Insights Dashboard',
                    'enhanced_description': 'Demographic and behavioral analysis of your target audiences'
                },
                'rnf_cumulative': {
                    'icon': '📡',
                    'title': 'Reach & Frequency Dashboard',
                    'enhanced_description': 'Cumulative reach and frequency trends with audience overlap analysis'
                },
                'rnf_overlap': {
                    'icon': '🔄',
                    'title': 'Audience Overlap Analysis',
                    'enhanced_description': 'Identify overlapping audiences between campaigns and ad sets'
                }
            }

            config = dashboard_config.get(job_type, {
                'icon': '📋',
                'title': job_name,
                'enhanced_description': description
            })

            if notebook_exists:
                title = f"{config['icon']} {config['title']}"
                enhanced_description = config['enhanced_description']
                
                # Handle special case for RnF job types (both use same dashboard)
                # Important: Include trailing slash to avoid 301 redirect that strips query params
                if job_type in ['rnf_cumulative', 'rnf_overlap']:
                    link = f"/rnf_dashboard/?account_id={selected_account_id}"
                else:
                    link = f"/{job_type}_dashboard/?account_id={selected_account_id}"

                stats = {
                    "Records": f"{record_count:,}" if job_has_data else "0",
                    "Last Updated": last_updated,
                    "Status": "✅ Data Available" if job_has_data else "📭 No Data"
                }

                if not job_has_data:
                    enhanced_description += " (No data available for this account)"

                card = create_dashboard_card(title, enhanced_description, link, stats)
                dashboard_cards.append(card)
            else:
                title = f"⚠️ {job_name}"
                description_text = f"{description} (Dashboard not available - notebook missing)"
                link = "#"

                stats = {
                    "Status": "❌ Unavailable",
                    "Records": f"{record_count:,}" if job_has_data else "0"
                }

                card = create_dashboard_card(title, description_text, link, stats)
                dashboard_cards.append(card)

        # Create output
        if dashboard_cards:
            _summary_available = len([d for d in dashboard_registry if d['notebook_exists']])
            _summary_data_count = len([d for d in dashboard_registry if d['data_stats']['has_data']])

            _dashboards_display = mo.vstack([
                mo.md("## Available Dashboards"),
                *dashboard_cards,
                mo.md(f"""
                ---
                **Dashboard Summary:** {_summary_available}/{len(dashboard_registry)} dashboards available • {_summary_data_count} with data across all accounts
                """)
            ])
        else:
            _dashboards_display = create_info_message(
                "No Dashboards Configured",
                "No dashboard types are configured in the system. Please add job types to the database."
            )
    else:
        _dashboards_display = mo.md("")

    _dashboards_display
    return


@app.cell
def _(mo):
    # Define management buttons
    refresh_dashboards_btn = mo.ui.button(
        label="🔄 Refresh Dashboards",
    )

    generate_missing_btn = mo.ui.button(
        label="🚀 Generate Missing Dashboards",
    )
    return generate_missing_btn, refresh_dashboards_btn


@app.cell
def _(
    accounts_df,
    generate_missing_btn,
    mo,
    refresh_dashboards_btn,
    selected_account_id,
):
    # Display account info and buttons - MUST output
    if selected_account_id and not accounts_df.empty:
        matching_accounts = accounts_df[accounts_df['account_id'] == selected_account_id]

        if not matching_accounts.empty:
            account_info = matching_accounts.iloc[0]

            _account_info_display = mo.vstack([
                mo.md(f"""
                ### Account Information

                **Account Name:** {account_info['account_name']}  
                **Account ID:** {account_info['account_id']}  
                **Last Updated:** {account_info['last_updated']}
                """),
                mo.md("### Dashboard Management"),
                mo.hstack([refresh_dashboards_btn, generate_missing_btn], justify="start")
            ])
        else:
            _account_info_display = mo.md(f"""
            ### Account Information

            **Account ID:** {selected_account_id}  
            **Status:** Account not found in database
            """)
    else:
        _account_info_display = mo.md("")

    _account_info_display
    return


@app.cell
def _(db_manager, mo):
    # System status and help - MUST output
    from utils.dashboard_factory import dashboard_factory as _df

    _dashboard_reg = _df.get_dashboard_registry()
    _total_dash = len(_dashboard_reg)
    _avail_dash = len([d for d in _dashboard_reg if d['notebook_exists']])
    _total_accts = len(db_manager.get_accounts())
    _db_connected = db_manager.test_connection()

    _system_status_display = mo.md(f"""
    ---

    ### System Status

    **Dashboards:** {_avail_dash}/{_total_dash} available  
    **Accounts:** {_total_accts} configured  
    **Database:** {"✅ Connected" if _db_connected else "❌ Disconnected"}

    ### Getting Started

    1. **Select an account** from the dropdown above
    2. **Click on a dashboard card** to view detailed analytics  
    3. **Use the browser back button** to return to this index page

    ### Troubleshooting

    **No dashboards showing?**
    - Ensure data extraction has been run for your accounts
    - Check that job types are registered in the database
    - Run the dashboard generation script: `uv run python scripts/generate_dashboards.py`

    **Missing data?**
    - Verify that the FastAPI service has extracted data for your account
    - Check the database tables contain records for your account ID
    - Ensure the account ID matches exactly between extraction and dashboard

    **Dashboard errors?**
    - Check that all required dependencies are installed
    - Verify database schema matches expected structure
    - Contact your administrator if problems persist
    """)

    _system_status_display
    return


if __name__ == "__main__":
    app.run()
