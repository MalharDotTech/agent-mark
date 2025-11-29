# Codebase Cleanup Design Document

## Overview

This design outlines the systematic cleanup of the Meta Ads API codebase to transition from a complex FastAPI + PostgreSQL + Metabase architecture to a simplified FastAPI + Marimo + SQLite approach. The cleanup will preserve the core Meta API pulling logic while removing all unnecessary components.

## Architecture

### Current Architecture (To Be Cleaned)
```
┌─────────────────────────────────────────────────────────────┐
│                   Current System                            │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐   ┌──────────────┐    │
│  │   FastAPI    │◄──►│  PostgreSQL  │◄─►│   Metabase   │    │
│  │              │    │              │   │              │    │
│  │ • Job System │    │ • Complex    │   │ • BI         │    │
│  │ • Database   │    │   Schema     │   │ • Dashboards │    │
│  │ • Meta API   │    │ • asyncpg    │   │ • Docker     │    │
│  └──────────────┘    └──────────────┘   └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Target Architecture (After Cleanup)
```
┌─────────────────────────────────────────────────────────────┐
│                   Cleaned System                            │
│                                                             │
│  ┌──────────────┐                                           │
│  │   FastAPI    │                                           │
│  │              │                                           │
│  │ • Meta API   │    (Ready for SQLite + Marimo)           │
│  │ • Token Mgmt │                                           │
│  │ • Rate Limit │                                           │
│  │ • Data Extr. │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Components to Preserve

#### 1. Meta API Client (`app/services/meta_client.py`)
- **Purpose**: Core Meta Graph API interactions
- **Preserve**: All HTTP client functionality, pagination, error handling
- **Dependencies**: httpx, token manager, rate limiter
- **Interface**: Async methods for accounts, campaigns, insights

#### 2. Token Manager (`app/core/token_manager.py`)
- **Purpose**: Multi-token rotation and management
- **Preserve**: Token rotation logic, availability tracking
- **Dependencies**: Core configuration
- **Interface**: Token selection and status methods

#### 3. Rate Limiter (`app/core/rate_limiter.py`)
- **Purpose**: API rate limiting with exponential backoff
- **Preserve**: Backoff algorithms, retry logic, error handling
- **Dependencies**: Token manager
- **Interface**: Request execution with automatic retry

#### 4. Data Extractor (`app/services/data_extractor.py`)
- **Purpose**: Data extraction with chunking and pagination
- **Preserve**: Chunking logic, concurrent processing, CSV output
- **Modifications**: Remove database integration, keep CSV functionality
- **Interface**: Extract methods returning data or CSV files

#### 5. Core Configuration (`app/core/config.py`)
- **Purpose**: Application configuration management
- **Preserve**: Meta API settings, token configuration
- **Remove**: PostgreSQL settings, Metabase configuration
- **Interface**: Settings access for preserved components

### Components to Remove

#### 1. Database Layer
- **Files**: `app/models/database.py`, `app/services/database.py`
- **Reason**: PostgreSQL-specific, not needed for SQLite approach
- **Dependencies**: asyncpg, database connection pooling

#### 2. Job Processing System
- **Files**: `app/services/job_processor.py`
- **Models**: Job request/response models in `app/models/`
- **Reason**: Complex background job system not needed for simplified approach
- **API Endpoints**: Job-related endpoints in `app/main.py`

#### 3. Database Models
- **Files**: Database-specific models and schemas
- **Reason**: PostgreSQL-specific table definitions
- **Dependencies**: asyncpg, database ORM functionality

#### 4. Test Files
- **Files**: `test_database_integration.py`, `test_populate_database.py`
- **Reason**: Test PostgreSQL and job system functionality
- **Keep**: `test_simple.py`, `test_with_account.py` (Meta API tests)

### Files to Update

#### 1. Main FastAPI Application (`app/main.py`)
- **Remove**: Database initialization, job endpoints
- **Preserve**: Meta API endpoints, health checks
- **Simplify**: Exception handlers, startup/shutdown events

#### 2. Configuration Files
- **Update**: `.env.example` - remove PostgreSQL variables
- **Remove**: Docker-related configuration files
- **Preserve**: Meta API configuration

#### 3. Documentation
- **Update**: `README.md` - remove PostgreSQL/Metabase references
- **Remove**: `arch.md` - outdated architecture diagrams
- **Update**: `project_context.md` - reflect new approach

## Data Models

### Preserved Data Structures

#### Meta API Response Models
```python
# Keep existing response models for Meta API data
class AccountInfo(BaseModel):
    account_id: str
    account_name: str

class InsightData(BaseModel):
    # Core insights data structure
    date: str
    impressions: int
    clicks: int
    spend: float
    # ... other Meta API fields
```

#### CSV Output Models
```python
# Keep CSV transformation logic
class CSVTransformer:
    @staticmethod
    def transform_to_csv_row(item: Dict, account_id: str, account_name: str) -> Dict
    
    @staticmethod
    def get_link_clicks(item: Dict) -> int
    
    @staticmethod
    def get_landing_page_views(item: Dict) -> int
```

### Removed Data Models
- Database table schemas
- Job status and progress models
- PostgreSQL-specific data types
- Database connection models

## Error Handling

### Preserved Error Handling
- **Meta API Exceptions**: Rate limiting, token errors, API errors
- **HTTP Exceptions**: Connection errors, timeout handling
- **Validation Exceptions**: Request parameter validation

### Simplified Error Handling
- Remove database-specific error handling
- Remove job processing error states
- Simplify exception hierarchy for core functionality

## Testing Strategy

### Tests to Preserve
1. **Meta API Client Tests**
   - Token management functionality
   - Rate limiting behavior
   - API response handling
   - Pagination logic

2. **Data Extraction Tests**
   - Chunking algorithms
   - CSV output format
   - Deduplication logic

3. **Integration Tests**
   - End-to-end Meta API data extraction
   - CSV file generation and validation

### Tests to Remove
1. **Database Integration Tests**
   - PostgreSQL connection tests
   - Database schema tests
   - Data persistence tests

2. **Job Processing Tests**
   - Background job execution
   - Job status tracking
   - Job queue management

### Test Environment Simplification
- Remove PostgreSQL test database setup
- Remove Docker test containers
- Focus on Meta API mocking and CSV validation

## Implementation Phases

### Phase 1: Analysis and Backup
1. Create backup of current codebase
2. Analyze dependencies and imports
3. Identify all files to be modified or removed
4. Document preserved functionality

### Phase 2: Remove Database Layer
1. Remove database service files
2. Remove database models and schemas
3. Remove asyncpg dependencies
4. Update imports and references

### Phase 3: Remove Job System
1. Remove job processor service
2. Remove job-related models
3. Remove job API endpoints
4. Simplify main application

### Phase 4: Clean Configuration
1. Remove PostgreSQL configuration
2. Remove Metabase references
3. Update environment files
4. Clean dependency lists

### Phase 5: Update Documentation
1. Update README and architecture docs
2. Remove outdated specifications
3. Update project context
4. Clean up example files

### Phase 6: Test and Validate
1. Run remaining tests
2. Validate Meta API functionality
3. Test CSV output generation
4. Verify configuration loading

## Migration Considerations

### Data Preservation
- No data migration needed (CSV-based output preserved)
- Configuration migration for essential settings only
- Token configuration remains unchanged

### Functionality Preservation
- All Meta API pulling logic preserved
- CSV output format maintained
- Rate limiting and token management unchanged
- Chunking and pagination logic preserved

### Breaking Changes
- Job API endpoints will be removed
- Database-related endpoints will be removed
- Background job processing will be removed
- PostgreSQL configuration will be invalid

## Dependencies Update

### Dependencies to Remove
```toml
# Remove from pyproject.toml
asyncpg = "*"           # PostgreSQL async driver
psycopg2-binary = "*"   # PostgreSQL driver
sqlalchemy = "*"        # Database ORM (if used)
alembic = "*"          # Database migrations (if used)
```

### Dependencies to Preserve
```toml
# Keep essential dependencies
fastapi = "*"           # Web framework
httpx = "*"            # HTTP client for Meta API
uvicorn = "*"          # ASGI server
python-dotenv = "*"    # Environment configuration
pydantic = "*"         # Data validation
```

### New Dependencies (Future)
```toml
# Will be added in future phases
sqlite3 = "*"          # Built-in SQLite support
marimo = "*"           # Notebook interface
```

## Validation Criteria

### Success Criteria
1. **Functionality Preserved**: Meta API data extraction works unchanged
2. **Clean Codebase**: No PostgreSQL or Metabase references remain
3. **Simplified Architecture**: Reduced complexity and dependencies
4. **Working Tests**: Core functionality tests pass
5. **Updated Documentation**: Reflects new simplified approach

### Validation Tests
1. **Meta API Connection**: Can authenticate and fetch accounts
2. **Data Extraction**: Can extract insights data to CSV
3. **Token Management**: Multi-token rotation works correctly
4. **Rate Limiting**: Handles API limits with proper backoff
5. **CSV Output**: Generates valid CSV files with correct format

## Risk Mitigation

### Backup Strategy
- Full codebase backup before cleanup
- Git branch for cleanup work
- Ability to rollback if issues arise

### Incremental Approach
- Remove components in phases
- Test after each phase
- Validate core functionality continuously

### Dependency Management
- Careful removal of imports
- Update requirements incrementally
- Test dependency resolution