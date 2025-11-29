# Requirements Document

## Introduction

This feature transforms the existing FastAPI Meta Ads service into a comprehensive dashboard architecture using Marimo notebooks as the primary UI layer, with SQLite database storage replacing CSV file outputs. The system will support multiple data job types through a modular notebook structure, with an index notebook providing navigation to specialized dashboard notebooks filtered by account selection.

## Glossary

- **FastAPI_Service**: The existing web service that handles Meta Ads API authentication and data extraction
- **Marimo_Index_Notebook**: The main navigation notebook that displays account listings and provides access to dashboard notebooks
- **Dashboard_Notebook**: Individual Marimo notebooks that display data visualizations and analytics for specific data job types
- **Data_Job_Type**: A specific category of data extraction (e.g., ad performance, audience insights, campaign metrics)
- **SQLite_Database**: The local database that stores extracted data with dedicated schemas for each data job type
- **Account_Selection**: The process of choosing specific Meta Ads accounts to filter dashboard data
- **Data_Schema**: The database table structure dedicated to a specific data job type

## Requirements

### Requirement 1

**User Story:** As a data analyst, I want to access a centralized index notebook, so that I can navigate to different dashboard notebooks based on my account and data type needs.

#### Acceptance Criteria

1. THE Marimo_Index_Notebook SHALL display a list of available Meta Ads accounts
2. WHEN an account is selected, THE Marimo_Index_Notebook SHALL show available data job types for that account
3. WHEN a data job type is selected, THE Marimo_Index_Notebook SHALL navigate to the corresponding Dashboard_Notebook
4. THE Marimo_Index_Notebook SHALL provide a clear navigation interface with account and data type filtering
5. THE Marimo_Index_Notebook SHALL connect to the SQLite_Database to retrieve account listings

### Requirement 2

**User Story:** As a data analyst, I want to view data in specialized dashboard notebooks, so that I can analyze specific data types with appropriate visualizations and filters.

#### Acceptance Criteria

1. THE Dashboard_Notebook SHALL display data filtered by the selected account_id
2. THE Dashboard_Notebook SHALL connect to its dedicated Data_Schema in the SQLite_Database
3. THE Dashboard_Notebook SHALL provide interactive visualizations appropriate for its data job type
4. THE Dashboard_Notebook SHALL include filtering and sorting capabilities for the displayed data
5. WHEN no data exists for the selected account, THE Dashboard_Notebook SHALL display an appropriate message

### Requirement 3

**User Story:** As a system administrator, I want the FastAPI service to store data in SQLite instead of CSV files, so that I can support multiple data job types with proper relational data management.

#### Acceptance Criteria

1. THE FastAPI_Service SHALL store extracted data in SQLite_Database tables instead of CSV files
2. THE FastAPI_Service SHALL create dedicated Data_Schema for each data job type
3. THE FastAPI_Service SHALL maintain existing API endpoints while changing the storage backend
4. THE FastAPI_Service SHALL provide database connection utilities for Marimo notebooks
5. THE SQLite_Database SHALL support concurrent read access from multiple Dashboard_Notebook instances

### Requirement 4

**User Story:** As a developer, I want a modular architecture that supports multiple data job types, so that I can easily add new dashboard notebooks and data schemas in the future.

#### Acceptance Criteria

1. THE system SHALL support adding new Data_Job_Type without modifying existing Dashboard_Notebook code
2. THE FastAPI_Service SHALL provide a standardized interface for different data job types
3. THE Marimo_Index_Notebook SHALL automatically discover available Dashboard_Notebook instances
4. THE SQLite_Database SHALL support dynamic schema creation for new data job types
5. THE system SHALL maintain separation between different Data_Schema to prevent data conflicts

### Requirement 5

**User Story:** As a project maintainer, I want comprehensive documentation and setup instructions, so that team members can understand and contribute to the new architecture.

#### Acceptance Criteria

1. THE project SHALL include updated README files explaining the new architecture
2. THE project SHALL provide setup instructions for Marimo notebook dependencies
3. THE project SHALL document the database schema structure and conventions
4. THE project SHALL include architecture diagrams showing component relationships
5. THE project SHALL provide examples of how to create new Dashboard_Notebook instances