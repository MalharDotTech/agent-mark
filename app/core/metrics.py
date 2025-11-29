"""Simple metrics collection for monitoring API calls and system performance."""

import time
from typing import Dict, Any, List
from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading

from .logging import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """
    Simple metrics collector for tracking API calls, response times, and error rates.
    
    Provides basic monitoring capabilities for Meta API service performance.
    """
    
    def __init__(self, max_history_minutes: int = 60):
        """
        Initialize metrics collector.
        
        Args:
            max_history_minutes: How long to keep metrics history in minutes
        """
        self.max_history_minutes = max_history_minutes
        self.lock = threading.Lock()
        
        # API call metrics
        self.api_calls: deque = deque()  # (timestamp, endpoint, method, success, response_time_ms)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_response_time_ms': 0,
            'min_response_time_ms': float('inf'),
            'max_response_time_ms': 0
        })
        
        logger.info(f"MetricsCollector initialized with {max_history_minutes}min history")
    
    def record_api_call(
        self, 
        endpoint: str, 
        method: str, 
        success: bool, 
        response_time_ms: float,
        error_type: str = None
    ):
        """
        Record an API call for metrics tracking.
        
        Args:
            endpoint: API endpoint called
            method: HTTP method (GET, POST, etc.)
            success: Whether the call was successful
            response_time_ms: Response time in milliseconds
            error_type: Type of error if call failed
        """
        timestamp = time.time()
        
        with self.lock:
            # Add to call history
            self.api_calls.append((timestamp, endpoint, method, success, response_time_ms))
            
            # Update endpoint statistics
            stats = self.endpoint_stats[f"{method} {endpoint}"]
            stats['total_calls'] += 1
            stats['total_response_time_ms'] += response_time_ms
            
            if success:
                stats['successful_calls'] += 1
            else:
                stats['failed_calls'] += 1
                if error_type:
                    self.error_counts[error_type] += 1
            
            # Update min/max response times
            stats['min_response_time_ms'] = min(stats['min_response_time_ms'], response_time_ms)
            stats['max_response_time_ms'] = max(stats['max_response_time_ms'], response_time_ms)
            
            # Clean old data
            self._cleanup_old_data(timestamp)
    
    def _cleanup_old_data(self, current_timestamp: float):
        """
        Remove old data beyond the history window.
        
        Args:
            current_timestamp: Current timestamp for comparison
        """
        cutoff_time = current_timestamp - (self.max_history_minutes * 60)
        
        # Clean API calls history
        while self.api_calls and self.api_calls[0][0] < cutoff_time:
            self.api_calls.popleft()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics summary.
        
        Returns:
            Dictionary with metrics data
        """
        with self.lock:
            current_time = time.time()
            cutoff_time = current_time - (self.max_history_minutes * 60)
            
            # Filter recent calls
            recent_calls = [call for call in self.api_calls if call[0] >= cutoff_time]
            
            if not recent_calls:
                return {
                    "time_window_minutes": self.max_history_minutes,
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "success_rate": 0.0,
                    "average_response_time_ms": 0.0,
                    "endpoints": {},
                    "error_counts": dict(self.error_counts),
                    "calls_per_minute": 0.0
                }
            
            # Calculate overall statistics
            total_calls = len(recent_calls)
            successful_calls = sum(1 for call in recent_calls if call[3])
            failed_calls = total_calls - successful_calls
            success_rate = (successful_calls / total_calls) * 100 if total_calls > 0 else 0.0
            
            # Calculate response time statistics
            response_times = [call[4] for call in recent_calls]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
            min_response_time = min(response_times) if response_times else 0.0
            max_response_time = max(response_times) if response_times else 0.0
            
            # Calculate calls per minute
            time_span_minutes = self.max_history_minutes
            calls_per_minute = total_calls / time_span_minutes if time_span_minutes > 0 else 0.0
            
            # Endpoint-specific statistics
            endpoint_metrics = {}
            for endpoint, stats in self.endpoint_stats.items():
                if stats['total_calls'] > 0:
                    endpoint_metrics[endpoint] = {
                        "total_calls": stats['total_calls'],
                        "successful_calls": stats['successful_calls'],
                        "failed_calls": stats['failed_calls'],
                        "success_rate": (stats['successful_calls'] / stats['total_calls']) * 100,
                        "average_response_time_ms": stats['total_response_time_ms'] / stats['total_calls'],
                        "min_response_time_ms": stats['min_response_time_ms'] if stats['min_response_time_ms'] != float('inf') else 0,
                        "max_response_time_ms": stats['max_response_time_ms']
                    }
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "time_window_minutes": self.max_history_minutes,
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "failed_calls": failed_calls,
                "success_rate": round(success_rate, 2),
                "average_response_time_ms": round(avg_response_time, 2),
                "min_response_time_ms": round(min_response_time, 2),
                "max_response_time_ms": round(max_response_time, 2),
                "calls_per_minute": round(calls_per_minute, 2),
                "endpoints": endpoint_metrics,
                "error_counts": dict(self.error_counts)
            }
    
    def get_recent_calls(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent API calls for debugging.
        
        Args:
            limit: Maximum number of calls to return
            
        Returns:
            List of recent API call records
        """
        with self.lock:
            recent_calls = list(self.api_calls)[-limit:]
            
            return [
                {
                    "timestamp": datetime.fromtimestamp(call[0]).isoformat(),
                    "endpoint": call[1],
                    "method": call[2],
                    "success": call[3],
                    "response_time_ms": call[4]
                }
                for call in recent_calls
            ]
    
    def reset_metrics(self):
        """Reset all metrics data."""
        with self.lock:
            self.api_calls.clear()
            self.error_counts.clear()
            self.endpoint_stats.clear()
            logger.info("Metrics data reset")


# Global metrics collector instance
metrics_collector = MetricsCollector()