# Requirements Document

## Introduction

This document outlines the requirements for cleaning up the existing Meta Ads API codebase to align with the new technical approach. The system will transition from a FastAPI + PostgreSQL + Metabase architecture to a simplified FastAPI + Marimo + SQLite architecture, preserving only the core Meta API pulling logic.

## Glossary

- **Meta_API_Client**: The core service responsible for interacting with Meta Graph API
- **Data_Extractor**: Service that handles data extraction and chunking logic
- **Token_Manager**: Service managing multiple Meta API access tokens with rotation
- **Rate_Limiter**: Service handling API rate limiting and exponential backoff
- **Cleanup_System**: The system responsible for removing obsolete code components
- **Core_Logic**: Essential Meta API pulling functionality that must be preserved

## Requirements

### Requirement 1

**User Story:** As a developer, I want to remove PostgreSQL dependencies, so that the codebase aligns with the new SQLite-based architecture

#### Acceptance Criteria

1. WHEN the cleanup process starts, THE Cleanup_System SHALL remove all PostgreSQL-related database models
2. WHEN removing database code, THE Cleanup_System SHALL remove all asyncpg dependencies and imports
3. WHEN cleaning database services, THE Cleanup_System SHALL remove the database service layer entirely
4. WHEN removing PostgreSQL code, THE Cleanup_System SHALL preserve the Meta API client and data extraction logic
5. WHERE PostgreSQL integration exists, THE Cleanup_System SHALL remove all related configuration and setup files

### Requirement 2

**User Story:** As a developer, I want to remove Metabase integration code, so that the codebase focuses on the new Marimo-based approach

#### Acceptance Criteria

1. WHEN cleaning Metabase code, THE Cleanup_System SHALL remove all Metabase-related documentation and references
2. WHEN removing BI integration, THE Cleanup_System SHALL remove Docker Compose configurations for Metabase
3. WHEN cleaning architecture docs, THE Cleanup_System SHALL remove Metabase from system diagrams and descriptions
4. THE Cleanup_System SHALL remove any Metabase-specific data formatting or preparation code

### Requirement 3

**User Story:** As a developer, I want to remove complex job processing systems, so that the codebase is simplified for the new approach

#### Acceptance Criteria

1. WHEN removing job systems, THE Cleanup_System SHALL remove the job processor service and related models
2. WHEN cleaning job code, THE Cleanup_System SHALL remove job status tracking and database persistence
3. WHEN removing background processing, THE Cleanup_System SHALL remove job-related API endpoints
4. THE Cleanup_System SHALL preserve the core data extraction functionality without job wrapper
5. WHERE job models exist, THE Cleanup_System SHALL remove job request and response models

### Requirement 4

**User Story:** As a developer, I want to preserve core Meta API functionality, so that the essential pulling logic remains intact

#### Acceptance Criteria

1. THE Meta_API_Client SHALL be preserved with all token management capabilities
2. THE Rate_Limiter SHALL be preserved with exponential backoff and retry logic
3. THE Token_Manager SHALL be preserved with multi-token rotation functionality
4. THE Data_Extractor SHALL be preserved with chunking and pagination logic
5. WHEN preserving core logic, THE Cleanup_System SHALL maintain all Meta Graph API interaction methods

### Requirement 5

**User Story:** As a developer, I want to remove Docker and deployment configurations, so that the codebase focuses on core functionality

#### Acceptance Criteria

1. WHEN cleaning deployment code, THE Cleanup_System SHALL remove Docker Compose files and configurations
2. WHEN removing containerization, THE Cleanup_System SHALL remove Dockerfile and related build scripts
3. WHEN cleaning infrastructure, THE Cleanup_System SHALL remove deployment documentation and setup guides
4. THE Cleanup_System SHALL preserve local development setup and configuration files

### Requirement 6

**User Story:** As a developer, I want to remove test files that are no longer relevant, so that the test suite aligns with the simplified architecture

#### Acceptance Criteria

1. WHEN cleaning tests, THE Cleanup_System SHALL remove PostgreSQL integration tests
2. WHEN removing test code, THE Cleanup_System SHALL remove database-specific test utilities
3. WHEN cleaning test files, THE Cleanup_System SHALL remove job processing tests
4. THE Cleanup_System SHALL preserve Meta API client tests and core functionality tests
5. WHERE test files reference removed components, THE Cleanup_System SHALL remove those test files

### Requirement 7

**User Story:** As a developer, I want to update configuration and documentation, so that they reflect the new simplified architecture

#### Acceptance Criteria

1. WHEN updating configuration, THE Cleanup_System SHALL remove PostgreSQL connection settings
2. WHEN cleaning config files, THE Cleanup_System SHALL remove Metabase-related environment variables
3. WHEN updating documentation, THE Cleanup_System SHALL remove references to removed components
4. THE Cleanup_System SHALL update README and architecture documentation to reflect new approach
5. WHERE specs reference removed components, THE Cleanup_System SHALL update or remove those specifications