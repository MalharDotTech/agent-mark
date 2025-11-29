"""
Common utilities for Marimo notebooks.
Provides shared functions for UI components, formatting, and navigation.
"""

import marimo as mo
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode


def format_currency(value: float) -> str:
    """Format numeric value as currency."""
    if value is None:
        return "$0.00"
    return f"${value:,.2f}"


def format_number(value: int) -> str:
    """Format large numbers with commas."""
    if value is None:
        return "0"
    return f"{value:,}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format decimal as percentage."""
    if value is None:
        return "0.00%"
    return f"{value:.{decimals}f}%"


def create_navigation_link(notebook_path: str, account_id: str, **params) -> str:
    """Create navigation link to another notebook with parameters."""
    query_params = {"account_id": account_id, **params}
    query_string = urlencode(query_params)
    return f"{notebook_path}?{query_string}"


def check_dashboard_availability(job_type_id: str) -> Dict[str, Any]:
    """Check if a dashboard is available and has data."""
    from pathlib import Path
    
    # Check if notebook file exists
    notebooks_dir = Path(__file__).parent.parent
    notebook_path = notebooks_dir / f"{job_type_id}_dashboard.py"
    notebook_exists = notebook_path.exists()
    
    # Check if job type is registered in database
    try:
        from .db_connection import db_manager
        job_types = db_manager.get_all_job_types()
        job_registered = not job_types[job_types['job_type_id'] == job_type_id].empty
    except Exception:
        job_registered = False
    
    return {
        'job_type_id': job_type_id,
        'notebook_exists': notebook_exists,
        'job_registered': job_registered,
        'available': notebook_exists and job_registered,
        'notebook_path': str(notebook_path)
    }


def get_url_param(param_name: str, default: Optional[str] = None) -> Optional[str]:
    """Get URL parameter from Marimo query params."""
    try:
        query_params = mo.query_params()
        return query_params.get(param_name, default)
    except:
        return default


def create_dashboard_card(title: str, description: str, link: str, stats: Optional[Dict[str, Any]] = None) -> mo.Html:
    """Create a dashboard navigation card."""
    stats_html = ""
    if stats:
        stats_items = []
        for key, value in stats.items():
            stats_items.append(f"<span>📊 {key}: {value}</span>")
        stats_html = f"""
        <div style="display: flex; gap: 20px; font-size: 14px; color: #999; margin-top: 12px;">
            {' '.join(stats_items)}
        </div>
        """
    
    return mo.Html(f"""
    <a href="{link}" style="text-decoration: none; color: inherit;">
        <div style="
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 24px;
            margin: 12px 0;
            background: white;
            transition: box-shadow 0.2s;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        " onmouseover="this.style.boxShadow='0 4px 8px rgba(0,0,0,0.15)'" 
           onmouseout="this.style.boxShadow='0 2px 4px rgba(0,0,0,0.1)'">
            <h3 style="margin: 0 0 8px 0; color: #333;">{title}</h3>
            <p style="color: #666; margin: 0; line-height: 1.4;">
                {description}
            </p>
            {stats_html}
        </div>
    </a>
    """)


def create_error_message(title: str, message: str, suggestion: Optional[str] = None) -> mo.Html:
    """Create a formatted error message."""
    suggestion_html = ""
    if suggestion:
        suggestion_html = f"<p style='margin: 8px 0 0 0; color: #666;'><strong>Suggestion:</strong> {suggestion}</p>"
    
    return mo.Html(f"""
    <div style="
        border: 1px solid #f5c6cb;
        border-radius: 8px;
        padding: 20px;
        margin: 16px 0;
        background: #f8d7da;
        color: #721c24;
    ">
        <h4 style="margin: 0 0 8px 0;">⚠️ {title}</h4>
        <p style="margin: 0;">{message}</p>
        {suggestion_html}
    </div>
    """)


def create_info_message(title: str, message: str) -> mo.Html:
    """Create a formatted info message."""
    return mo.Html(f"""
    <div style="
        border: 1px solid #b8daff;
        border-radius: 8px;
        padding: 20px;
        margin: 16px 0;
        background: #d1ecf1;
        color: #0c5460;
    ">
        <h4 style="margin: 0 0 8px 0;">ℹ️ {title}</h4>
        <p style="margin: 0;">{message}</p>
    </div>
    """)


def create_warning_message(title: str, message: str, suggestion: Optional[str] = None) -> mo.Html:
    """Create a formatted warning message."""
    suggestion_html = ""
    if suggestion:
        suggestion_html = f"<p style='margin: 8px 0 0 0; color: #856404;'><strong>Suggestion:</strong> {suggestion}</p>"
    
    return mo.Html(f"""
    <div style="
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 20px;
        margin: 16px 0;
        background: #fff3cd;
        color: #856404;
    ">
        <h4 style="margin: 0 0 8px 0;">⚠️ {title}</h4>
        <p style="margin: 0;">{message}</p>
        {suggestion_html}
    </div>
    """)


def create_unavailable_dashboard_card(title: str, description: str, reason: str) -> mo.Html:
    """Create a card for unavailable dashboards."""
    return mo.Html(f"""
    <div style="
        border: 1px solid #f5c6cb;
        border-radius: 8px;
        padding: 24px;
        margin: 12px 0;
        background: #f8f9fa;
        opacity: 0.7;
        cursor: not-allowed;
    ">
        <h3 style="margin: 0 0 8px 0; color: #6c757d;">🚫 {title}</h3>
        <p style="color: #6c757d; margin: 0 0 12px 0; line-height: 1.4;">
            {description}
        </p>
        <div style="font-size: 14px; color: #dc3545;">
            <strong>Unavailable:</strong> {reason}
        </div>
    </div>
    """)