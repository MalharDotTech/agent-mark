"""
CSV output models and transformation functions for Meta Ads data.
"""
from typing import Dict, Any, List, Tuple
from pydantic import BaseModel, Field


class CSVRow(BaseModel):
    """Model representing a single CSV row for Meta Ads data."""
    
    Date: str = Field(..., description="Date of the data (YYYY-MM-DD)")
    Account_ID: str = Field(..., description="Meta ad account ID")
    Account_Name: str = Field(..., description="Meta ad account name")
    Campaign_Name: str = Field(..., description="Campaign name")
    Campaign_ID: str = Field(..., description="Campaign ID")
    Ad_set_Name: str = Field(..., description="Ad set name")
    Ad_set_ID: str = Field(..., description="Ad set ID")
    Ad_Name: str = Field(..., description="Ad name")
    Ad_ID: str = Field(..., description="Ad ID")
    Publisher_Platform: str = Field(..., description="Publisher platform")
    Platform_Position: str = Field(..., description="Platform position")
    Impressions: str = Field(..., description="Number of impressions")
    Clicks: str = Field(..., description="Number of link clicks")
    Spends: str = Field(..., description="Amount spent")
    Landing_Page_Views: str = Field(..., description="Number of landing page views")


class CSVTransformer:
    """Handles transformation of Meta API data to CSV format."""
    
    # CSV headers matching the working script
    CSV_HEADERS = [
        "Date", "Account ID", "Account Name",
        "Campaign Name", "Campaign ID",
        "Ad-set Name", "Ad set ID", 
        "Ad Name", "Ad ID",
        "Publisher_Platform", "Platform_Position",
        "Impressions", "Clicks", "Spends", "Landing Page Views"
    ]
    
    @staticmethod
    def extract_action_value(row: Dict[str, Any], action_type: str) -> int:
        """
        Extract action value from Meta API response actions array.
        
        Args:
            row: Meta API response row
            action_type: Type of action to extract (e.g., 'link_click', 'landing_page_view')
            
        Returns:
            Total value for the specified action type
        """
        total = 0
        actions = row.get("actions") or []
        
        for action in actions:
            if action.get("action_type") == action_type:
                try:
                    value = action.get("value", 0) or 0
                    total += int(float(value))
                except (ValueError, TypeError):
                    continue
                    
        return total
    
    @staticmethod
    def get_link_clicks(row: Dict[str, Any]) -> int:
        """
        Get link clicks count, preferring action-based link_click over inline_link_clicks.
        
        Args:
            row: Meta API response row
            
        Returns:
            Number of link clicks
        """
        # First try to get from actions (preferred)
        link_clicks = CSVTransformer.extract_action_value(row, "link_click")
        
        if link_clicks > 0:
            return link_clicks
            
        # Fallback to inline_link_clicks
        try:
            inline_clicks = row.get("inline_link_clicks", 0) or 0
            return int(float(inline_clicks))
        except (ValueError, TypeError):
            return 0
    
    @staticmethod
    def get_landing_page_views(row: Dict[str, Any]) -> int:
        """
        Get landing page views count from actions.
        
        Args:
            row: Meta API response row
            
        Returns:
            Number of landing page views
        """
        return CSVTransformer.extract_action_value(row, "landing_page_view")
    
    @staticmethod
    def textify_id(value: Any) -> str:
        """
        Convert ID values to plain text strings (no formulas or hidden characters).
        
        Args:
            value: ID value to convert
            
        Returns:
            Plain string representation of the ID
        """
        return str(value) if value is not None else ""
    
    @staticmethod
    def make_dedup_key(item: Dict[str, Any], account_id: str) -> Tuple:
        """
        Create a composite key for deduplication across retries.
        
        Args:
            item: Meta API response item
            account_id: Account ID
            
        Returns:
            Tuple representing unique key for the record
        """
        return (
            account_id,
            item.get("date_stop") or item.get("date_start") or "",
            item.get("campaign_id", ""),
            item.get("adset_id", ""),
            item.get("ad_id", ""),
            item.get("publisher_platform", ""),
            item.get("platform_position", ""),
        )
    
    @staticmethod
    def transform_to_csv_row(
        item: Dict[str, Any], 
        account_id: str, 
        account_name: str = ""
    ) -> Dict[str, str]:
        """
        Transform a Meta API response item to CSV row format.
        
        Args:
            item: Meta API response item
            account_id: Account ID
            account_name: Account name (optional)
            
        Returns:
            Dictionary representing a CSV row
        """
        return {
            "Date": item.get("date_stop") or item.get("date_start") or "",
            "Account ID": CSVTransformer.textify_id(account_id),
            "Account Name": account_name or "",
            "Campaign Name": item.get("campaign_name", ""),
            "Campaign ID": CSVTransformer.textify_id(item.get("campaign_id", "")),
            "Ad-set Name": item.get("adset_name", ""),
            "Ad set ID": CSVTransformer.textify_id(item.get("adset_id", "")),
            "Ad Name": item.get("ad_name", ""),
            "Ad ID": CSVTransformer.textify_id(item.get("ad_id", "")),
            "Publisher_Platform": item.get("publisher_platform", ""),
            "Platform_Position": item.get("platform_position", ""),
            "Impressions": item.get("impressions", "0"),
            "Clicks": str(CSVTransformer.get_link_clicks(item)),
            "Spends": item.get("spend", "0"),
            "Landing Page Views": str(CSVTransformer.get_landing_page_views(item)),
        }


class CSVConfig:
    """Configuration for CSV output."""
    
    # CSV encoding and error handling (matching working script)
    ENCODING = "latin-1"
    ERRORS = "replace"
    
    # Default output filename
    DEFAULT_FILENAME = "meta_ads_data.csv"
    
    # Buffer size for writing
    BUFFER_SIZE = 8 * 1024 * 1024  # 8MB buffer