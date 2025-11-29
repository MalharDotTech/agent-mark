# Meta API Application Analysis & Rebuild Guide

## Overview

This document provides a comprehensive analysis of two Meta (Facebook) API applications built for data extraction and dashboard visualization. The applications demonstrate sophisticated approaches to handling Meta's Graph API for advertising insights, with focus on rate limiting, token management, and data visualization.

## Application Architecture

### 1. Data Pulling Application (`Data pulling - currently most optimised code.py`)

**Purpose**: Robust, high-performance data extraction from Meta Ads API to CSV format

**Key Features**:
- Multi-account data extraction
- Concurrent processing with thread pools
- Advanced rate limiting and token rotation
- Automatic retry mechanisms with exponential backoff
- Memory-efficient streaming and buffered CSV writing
- Transport-level error recovery

### 2. Dashboard Application (`Reach & Frequency Dashboard for views.py`)

**Purpose**: Interactive Streamlit dashboard for reach, frequency, and audience overlap analysis

**Key Features**:
- Real-time data visualization with Plotly
- Cumulative reach & frequency analysis
- Audience overlap calculations
- Multi-token load balancing
- Cached data operations

## Meta Graph API Integration

### API Version & Endpoints
- **API Version**: v23.0 (data puller) / v19.0 (dashboard)
- **Base URL**: `https://graph.facebook.com/{version}`
- **Primary Endpoints**:
  - `/me/adaccounts` - Account listing
  - `/act_{account_id}/insights` - Advertising insights
  - `/act_{account_id}/campaigns` - Campaign data
  - `/act_{account_id}/adsets` - Ad set data
  - `/act_{account_id}/ads` - Ad data

### Authentication & Token Management

#### Multi-Token Strategy
```python
# Token pool with round-robin distribution
class TokenPool:
    def __init__(self, tokens: List[str]):
        self.tokens = list(tokens)
        self.cooldowns: Dict[int, float] = {}
        self.lock = threading.Lock()
        self.ptr = 0
```

**Benefits**:
- Distributes API load across multiple tokens
- Automatic cooldown management for rate-limited tokens
- Thread-safe token rotation

#### Token Configuration
- **Data Puller**: Hardcoded token array in `ACCESS_TOKENS`
- **Dashboard**: Streamlit secrets with fallback pattern (`access_token_1`, `access_token_2`, etc.)

### Rate Limiting Strategy

#### Sophisticated Error Handling
```python
# Rate limit codes handled:
- Code 4: Application request limit reached
- Code 17: User request limit reached  
- Code 32: Page request limit reached
- Code 613: Rate limit exceeded
```

#### Backoff Mechanisms
- **Exponential backoff**: `base * (2^attempt) + random_jitter`
- **Token cooldowns**: 12-25 seconds based on error type
- **Transport recovery**: Client recreation on connection errors

### Data Extraction Patterns

#### Chunking Strategy
```python
# Month-based chunking with weekly sub-chunks
def month_chunks(start: str, end: str) -> List[Tuple[str, str]]
def sub_chunks(since: str, until: str, step_days: int) -> List[Tuple[str,str]]
```

**Benefits**:
- Reduces API timeout risks
- Enables parallel processing
- Facilitates retry of failed chunks

#### Pagination Handling
```python
# Cursor-based pagination
while True:
    if after: call["after"] = after
    payload = fb_get_json(url, call, token_pool, http)
    # Process data...
    after = cursors.get("after")
    if not after: break
```

## Performance Optimizations

### HTTP Client Management
- **Per-worker clients**: Avoids shared state issues
- **HTTP/2 support**: Uses httpx when available, falls back to requests
- **Connection pooling**: Configurable pool sizes
- **Client recreation**: Handles transport errors gracefully

### Concurrency Architecture
```python
# Thread pool with configurable workers
MAX_WORKERS = max(4, min(10, len(ACCESS_TOKENS) * 2 + 2))

# Separate threads for:
- Data fetching workers
- CSV writing (buffered)
- Progress reporting
```

### Memory Management
- **Streaming processing**: Data flows through queues
- **Buffered writing**: 8MB buffer for CSV output
- **Deduplication**: Global key-based dedup across retries

## Data Models & Transformations

### Core Metrics Extracted
```python
FIELDS = [
    "campaign_name", "campaign_id",
    "adset_name", "adset_id", 
    "ad_name", "ad_id",
    "impressions", "spend",
    "inline_link_clicks", "actions",
    "date_start", "date_stop"
]

BREAKDOWNS = ["publisher_platform", "platform_position"]
ACTION_BREAKDOWNS = ["action_type"]
```

### Data Transformations
- **Link Clicks**: Prioritizes `link_click` action over `inline_link_clicks`
- **Landing Page Views**: Extracted from actions array
- **ID Formatting**: Plain number strings (no Excel formulas)
- **Date Handling**: ISO format with proper chunking

### Output Schema
```csv
Date, Account ID, Account Name, Campaign Name, Campaign ID,
Ad-set Name, Ad set ID, Ad Name, Ad ID, Publisher_Platform,
Platform_Position, Impressions, Clicks, Spends, Landing Page Views
```

## Dashboard Features

### Cumulative Analysis
- **Reach Growth**: Tracks unique user reach over time
- **Frequency Trends**: Average impressions per user
- **Spend Accumulation**: Budget consumption patterns
- **Performance Metrics**: CPM, CPP, CTR calculations

### Audience Overlap Analysis
```python
# Overlap calculation formula:
overlap = reach1 + reach2 - combined_reach
overlap_percentage = (overlap / min_reach) * 100
```

**Methods**:
1. **Individual Reach**: Separate API calls per item
2. **Combined Reach**: Single call with multiple item filter
3. **Pairwise Analysis**: Exact overlap for all combinations

### Visualization Components
- **Plotly Charts**: Interactive time series, bar charts, heatmaps
- **Streamlit Metrics**: Key performance indicators
- **Data Tables**: Formatted numerical displays
- **Export Functions**: CSV download capabilities

## Technical Implementation Details

### Error Recovery Patterns
```python
# Multi-level retry with different strategies:
1. Transport errors → Client recreation
2. Rate limits → Token cooldown + backoff
3. Chunk failures → Sequential retry pass
4. Global dedup → Prevents data loss
```

### Configuration Management
```python
# Environment-specific settings:
- API_VERSION: Graph API version
- LOCALE: Response localization
- TIME_INCREMENT: Data granularity
- LIMIT_PER_PAGE: Pagination size
- CSV_ENCODING: Output encoding (latin-1)
```

### Monitoring & Logging
- **Progress tracking**: Real-time row count and rate
- **Detailed logging**: Timestamped error messages
- **Performance metrics**: Rows/second calculations
- **Failure tracking**: Failed chunk collection

## FastAPI Rebuild Recommendations

### 1. Architecture Design

#### API Structure
```python
# Suggested FastAPI endpoints:
POST /api/v1/extract/start     # Start extraction job
GET  /api/v1/extract/{job_id}  # Check job status
GET  /api/v1/extract/{job_id}/download  # Download results
POST /api/v1/analysis/reach    # Cumulative analysis
POST /api/v1/analysis/overlap  # Overlap analysis
GET  /api/v1/accounts         # List accounts
```

#### Background Processing
- **Celery/RQ**: Async task processing for long-running extractions
- **WebSocket**: Real-time progress updates
- **Redis**: Job status and result caching
- **PostgreSQL**: Job metadata and user management

### 2. Token Management Service
```python
class TokenManager:
    def __init__(self):
        self.tokens = self._load_tokens()
        self.cooldowns = {}
        self.usage_stats = {}
    
    async def get_available_token(self) -> str:
        # Round-robin with cooldown awareness
    
    async def report_rate_limit(self, token: str, cooldown_seconds: int):
        # Update cooldown status
```

### 3. Data Pipeline Architecture
```python
# Suggested pipeline stages:
1. Job Creation → Validation → Chunking
2. Parallel Extraction → Rate Limiting → Error Handling  
3. Data Transformation → Deduplication → Storage
4. Result Aggregation → Export Generation
```

### 4. API Client Abstraction
```python
class MetaAPIClient:
    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
        self.session = aiohttp.ClientSession()
    
    async def get_insights(self, account_id: str, params: dict) -> dict:
        # Async API calls with retry logic
    
    async def paginate_results(self, url: str, params: dict) -> AsyncIterator:
        # Async pagination handling
```

### 5. Dashboard Backend
```python
# FastAPI + React/Vue.js architecture:
- FastAPI: REST API backend
- React/Vue: Interactive frontend
- WebSocket: Real-time updates
- Plotly.js: Client-side visualizations
- Redis: Caching layer
```

### 6. Configuration Management
```python
# Pydantic settings:
class Settings(BaseSettings):
    meta_api_version: str = "v23.0"
    max_workers: int = 10
    chunk_size_days: int = 7
    rate_limit_cooldown: int = 25
    
    class Config:
        env_file = ".env"
```

### 7. Monitoring & Observability
- **Prometheus**: Metrics collection (API calls, success rates, latencies)
- **Grafana**: Dashboard visualization
- **Sentry**: Error tracking and alerting
- **Structured logging**: JSON logs with correlation IDs

### 8. Security Considerations
- **Token encryption**: Encrypt stored access tokens
- **Rate limiting**: API endpoint protection
- **Authentication**: JWT-based user auth
- **CORS**: Proper cross-origin configuration
- **Input validation**: Pydantic models for all inputs

### 9. Scalability Features
- **Horizontal scaling**: Multiple worker instances
- **Load balancing**: Distribute API calls across tokens/workers
- **Caching**: Redis for frequently accessed data
- **Database optimization**: Proper indexing and connection pooling

### 10. Testing Strategy
```python
# Test categories:
1. Unit tests: Individual functions and classes
2. Integration tests: API client interactions
3. Load tests: Rate limiting and concurrency
4. End-to-end tests: Complete extraction workflows
```

## Key Learnings for Rebuild

### 1. Meta API Challenges
- **Rate limiting**: Aggressive and unpredictable
- **Token management**: Critical for scale
- **Data consistency**: Requires careful deduplication
- **Error handling**: Must be comprehensive and resilient

### 2. Performance Patterns
- **Chunking**: Essential for large date ranges
- **Concurrency**: Balanced with rate limits
- **Streaming**: Memory-efficient processing
- **Caching**: Reduces redundant API calls

### 3. User Experience
- **Progress feedback**: Real-time status updates
- **Error communication**: Clear, actionable messages
- **Data export**: Multiple format options
- **Visualization**: Interactive and responsive

### 4. Operational Requirements
- **Monitoring**: Comprehensive observability
- **Alerting**: Proactive issue detection
- **Backup**: Data and configuration redundancy
- **Documentation**: API and user guides

This analysis provides the foundation for rebuilding these applications using modern FastAPI architecture while preserving the sophisticated Meta API integration patterns and performance optimizations demonstrated in the original code.