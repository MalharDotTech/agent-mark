# Implementation Plan

- [x] 1. Set up SQLite database foundation
  - Create SQLite database schema with accounts, data_job_types, and ad_performance_data tables
  - Implement database initialization script with proper table creation
  - Add database utilities for connection management and basic queries
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 2. Modify FastAPI service for SQLite storage
  - [x] 2.1 Replace CSV output with SQLite database storage in data extraction service
    - Update MetaAPIClient or create new DataExtractionService to store insights data in SQLite
    - Modify existing data extraction logic to insert records into ad_performance_data table
    - Ensure account information is stored in accounts table during extraction
    - _Requirements: 3.1, 3.2_

  - [x] 2.2 Add new database-focused API endpoints
    - Create GET /api/v1/job-types endpoint to list available job types
    - Create GET /api/v1/data/{job_type}/{account_id} endpoint to retrieve stored data
    - Update existing /api/v1/accounts endpoint to work with SQLite accounts table
    - _Requirements: 3.4, 4.1_

  - [x] 2.3 Update configuration for SQLite database path
    - Add SQLite database path configuration to settings
    - Remove PostgreSQL-related configuration that's no longer needed
    - Update health check endpoint to verify SQLite database connectivity
    - _Requirements: 3.3_

- [x] 3. Create Marimo notebook infrastructure
  - [x] 3.1 Set up basic Marimo project structure
    - Create notebooks directory with proper organization
    - Add Marimo dependencies to project requirements
    - Create shared database connection utilities for notebooks
    - _Requirements: 1.1, 1.5_

  - [x] 3.2 Implement Index notebook for account selection and navigation
    - Create index.py notebook that connects to SQLite database
    - Implement account listing interface using Marimo UI components
    - Add job type selection and navigation to dashboard notebooks
    - Include basic styling and layout for the index interface
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 3.3 Create first dashboard notebook for ad performance data
    - Create ad_performance_dashboard.py notebook with SQLite connection
    - Implement account_id filtering and data retrieval from ad_performance_data table
    - Add basic data visualizations using plotly or similar charting library
    - Include interactive filtering and sorting capabilities for the displayed data
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 4. Implement modular dashboard system
  - [x] 4.1 Create dashboard template system for future job types
    - Design reusable notebook template structure for new dashboard types
    - Implement dynamic job type discovery from database
    - Create utilities for automatic dashboard notebook generation
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 4.2 Enhance Index notebook with dynamic dashboard discovery
    - Update index notebook to automatically discover available dashboard notebooks
    - Implement dynamic navigation based on available job types in database
    - Add error handling for missing data or unavailable dashboards
    - _Requirements: 1.3, 4.3, 2.5_

- [x] 5. Update project documentation and setup
  - [x] 5.1 Update README with new Marimo-based architecture
    - Document the new architecture with FastAPI + SQLite + Marimo setup
    - Provide installation instructions for Marimo dependencies
    - Include setup instructions for database initialization
    - _Requirements: 5.1, 5.2_

  - [x] 5.2 Create setup scripts and development documentation
    - Create database initialization script for easy setup
    - Add development workflow documentation for adding new dashboard notebooks
    - Include architecture diagrams and component relationship documentation
    - Document the account → job type → dashboard relationship model
    - _Requirements: 5.3, 5.4, 5.5_