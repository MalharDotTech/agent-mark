"""
Dashboard Factory for Dynamic Dashboard Creation
Provides utilities for automatically creating and managing dashboard notebooks.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from .template_generator import DashboardTemplateGenerator, JobTypeConfig

logger = logging.getLogger(__name__)


class DashboardFactory:
    """Factory for creating and managing dashboard notebooks."""
    
    def __init__(self, db_path: Optional[str] = None, notebooks_dir: Optional[Path] = None):
        """Initialize dashboard factory."""
        self.template_generator = DashboardTemplateGenerator(db_path)
        
        if notebooks_dir is None:
            self.notebooks_dir = Path(__file__).parent.parent
        else:
            self.notebooks_dir = Path(notebooks_dir)
    
    def discover_and_create_dashboards(self) -> List[Dict[str, Any]]:
        """Discover job types and create missing dashboard notebooks."""
        job_types = self.template_generator.discover_job_types()
        results = []
        
        for job_config in job_types:
            result = self._ensure_dashboard_exists(job_config)
            results.append(result)
        
        return results
    
    def _ensure_dashboard_exists(self, job_config: JobTypeConfig) -> Dict[str, Any]:
        """Ensure a dashboard notebook exists for the job type."""
        notebook_filename = f"{job_config.job_type_id}_dashboard.py"
        notebook_path = self.notebooks_dir / notebook_filename
        
        result = {
            'job_type_id': job_config.job_type_id,
            'job_name': job_config.job_name,
            'notebook_filename': notebook_filename,
            'notebook_path': str(notebook_path),
            'existed': notebook_path.exists(),
            'created': False,
            'error': None
        }
        
        if not notebook_path.exists():
            try:
                self.template_generator.create_dashboard_notebook(job_config, self.notebooks_dir)
                result['created'] = True
                logger.info(f"Created dashboard notebook for {job_config.job_type_id}")
            except Exception as e:
                result['error'] = str(e)
                logger.error(f"Failed to create dashboard for {job_config.job_type_id}: {e}")
        
        return result
    
    def get_dashboard_registry(self) -> List[Dict[str, Any]]:
        """Get registry of all available dashboards."""
        job_types = self.template_generator.discover_job_types()
        registry = []
        
        for job_config in job_types:
            notebook_filename = f"{job_config.job_type_id}_dashboard.py"
            notebook_path = self.notebooks_dir / notebook_filename
            
            # Special case: RNF dashboards use a unified rnf_dashboard.py
            if job_config.job_type_id in ['rnf_cumulative', 'rnf_overlap']:
                unified_rnf_path = self.notebooks_dir / 'rnf_dashboard.py'
                notebook_exists = unified_rnf_path.exists()
            else:
                notebook_exists = notebook_path.exists()
            
            # Get data statistics
            data_stats = self._get_data_statistics(job_config)
            
            registry.append({
                'job_type_id': job_config.job_type_id,
                'job_name': job_config.job_name,
                'description': job_config.description,
                'table_name': job_config.table_name,
                'notebook_filename': notebook_filename,
                'notebook_exists': notebook_exists,
                'is_active': job_config.is_active,
                'primary_metrics': job_config.primary_metrics,
                'chart_types': job_config.chart_types,
                'data_stats': data_stats
            })
        
        return registry
    
    def _get_data_statistics(self, job_config: JobTypeConfig) -> Dict[str, Any]:
        """Get data statistics for a job type."""
        try:
            with self.template_generator.get_connection() as conn:
                # Get total record count
                cursor = conn.execute(f"SELECT COUNT(*) as total_records FROM {job_config.table_name}")
                total_records = cursor.fetchone()['total_records']
                
                # Get account count
                cursor = conn.execute(f"SELECT COUNT(DISTINCT account_id) as account_count FROM {job_config.table_name}")
                account_count = cursor.fetchone()['account_count']
                
                # Get date range
                date_columns = ['date_start', 'date_stop', 'extracted_at', 'created_at', 'updated_at']
                date_col = None
                for col in date_columns:
                    cursor = conn.execute(f"PRAGMA table_info({job_config.table_name})")
                    columns = [row['name'] for row in cursor.fetchall()]
                    if col in columns:
                        date_col = col
                        break
                
                date_range = None
                if date_col:
                    cursor = conn.execute(f"""
                        SELECT 
                            MIN({date_col}) as min_date,
                            MAX({date_col}) as max_date
                        FROM {job_config.table_name}
                    """)
                    date_result = cursor.fetchone()
                    if date_result['min_date'] and date_result['max_date']:
                        date_range = {
                            'min_date': date_result['min_date'],
                            'max_date': date_result['max_date']
                        }
                
                return {
                    'total_records': total_records,
                    'account_count': account_count,
                    'date_range': date_range,
                    'has_data': total_records > 0
                }
        except Exception as e:
            logger.error(f"Failed to get data statistics for {job_config.job_type_id}: {e}")
            return {
                'total_records': 0,
                'account_count': 0,
                'date_range': None,
                'has_data': False,
                'error': str(e)
            }
    
    def create_dashboard_for_job_type(self, job_type_id: str) -> Dict[str, Any]:
        """Create a dashboard for a specific job type."""
        job_types = self.template_generator.discover_job_types()
        job_config = None
        
        for jt in job_types:
            if jt.job_type_id == job_type_id:
                job_config = jt
                break
        
        if not job_config:
            return {
                'success': False,
                'error': f"Job type '{job_type_id}' not found in database"
            }
        
        try:
            notebook_path = self.template_generator.create_dashboard_notebook(job_config, self.notebooks_dir)
            return {
                'success': True,
                'job_type_id': job_type_id,
                'notebook_path': str(notebook_path),
                'job_name': job_config.job_name
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def refresh_all_dashboards(self) -> List[Dict[str, Any]]:
        """Refresh all dashboard notebooks by regenerating them."""
        job_types = self.template_generator.discover_job_types()
        results = []
        
        for job_config in job_types:
            try:
                notebook_path = self.template_generator.create_dashboard_notebook(job_config, self.notebooks_dir)
                results.append({
                    'job_type_id': job_config.job_type_id,
                    'success': True,
                    'notebook_path': str(notebook_path)
                })
            except Exception as e:
                results.append({
                    'job_type_id': job_config.job_type_id,
                    'success': False,
                    'error': str(e)
                })
        
        return results


# Global instance for easy import
dashboard_factory = DashboardFactory()