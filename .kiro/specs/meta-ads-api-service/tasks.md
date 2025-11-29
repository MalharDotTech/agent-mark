# Implementation Plan

- [x] 1. Set up basic project structure and configuration
  - Create simple directory structure (app/, core/, services/)
  - Set up basic Pydantic settings for environment variables
  - Configure simple logging with timestamps
  - _Requirements: 7.1, 8.1_

- [x] 2. Create simple token management
  - [x] 2.1 Build TokenManager class based on existing code
    - Implement round-robin token rotation from the working Python script
    - Add basic cooldown tracking for rate-limited tokens
    - Keep it simple with threading locks like the original code
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 2.2 Add basic rate limiting with backoff
    - Create simple rate limiter handling Meta API error codes (4, 17, 32, 613)
    - Implement exponential backoff with jitter (copy from working script)
    - Add token cooldown management when rate limits hit
    - _Requirements: 2.1, 2.2, 2.3_

- [x] 3. Build Meta API client (simplified version)
  - [x] 3.1 Create MetaAPIClient using httpx
    - Set up basic HTTP client with connection pooling
    - Implement core methods for Meta Graph API v23.0 endpoints
    - Add simple request/response logging
    - _Requirements: 1.3, 7.1_

  - [x] 3.2 Add pagination and basic chunking
    - Implement cursor-based pagination from the working script
    - Create simple date chunking (weekly chunks like original)
    - Keep concurrent processing simple with basic threading
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 3.3 Connect token manager and rate limiter
    - Integrate TokenManager with MetaAPIClient
    - Add RateLimiter to all API calls
    - Handle transport errors with client recreation
    - _Requirements: 2.1, 2.2, 3.1_

- [x] 4. Create basic data models
  - [x] 4.1 Build simple Pydantic models
    - Create ExtractionRequest model with basic validation
    - Add simple response models for job status
    - Keep error responses simple with basic fields
    - _Requirements: 1.1, 1.2, 8.3_

  - [x] 4.2 Design CSV output format
    - Use the same CSV structure as the working script
    - Implement data transformation functions (link clicks, landing page views)
    - Add simple deduplication using the same key logic
    - _Requirements: 6.3, 6.4_

- [x] 5. Create simple job processing
  - [x] 5.1 Build basic JobProcessor
    - Create simple job tracking with in-memory storage
    - Implement basic job states (pending, running, completed, failed)
    - Add simple progress tracking
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 5.2 Build DataExtractor for CSV output
    - Create data extraction that writes directly to CSV files
    - Use the same chunking and processing logic as working script
    - Add simple retry logic for failed chunks
    - _Requirements: 4.1, 4.2, 4.4_

- [x] 6. Build FastAPI application
  - [x] 6.1 Create main FastAPI app
    - Set up basic FastAPI application with simple middleware
    - Add basic CORS and exception handling
    - Keep it simple with minimal configuration
    - _Requirements: 1.1, 7.2_

  - [x] 6.2 Add extraction endpoints
    - Create POST /api/v1/extract/start endpoint
    - Add GET /api/v1/extract/{job_id} for status
    - Implement GET /api/v1/extract/{job_id}/download for CSV download
    - _Requirements: 1.1, 1.2, 5.3_

  - [x] 6.3 Add utility endpoints
    - Implement GET /api/v1/accounts for account listing
    - Create simple GET /health endpoint
    - _Requirements: 1.3, 7.3_

- [x] 7. Add basic error handling
  - [x] 7.1 Create simple exception handling
    - Add basic custom exceptions for Meta API errors
    - Implement simple global exception handler
    - Add basic error logging with timestamps
    - _Requirements: 7.1, 7.2_

  - [x] 7.2 Add basic monitoring
    - Simple logging for API calls and responses
    - Basic health checks for Meta API connectivity
    - Simple progress tracking and status updates
    - _Requirements: 7.3, 7.4_

- [x] 8. Environment setup and configuration
  - [x] 8.1 Create .env configuration
    - Set up environment variables for Meta API tokens
    - Add basic configuration for API settings
    - Create simple development configuration
    - _Requirements: 8.1, 8.2_

  - [x] 8.2 Add basic dependencies to pyproject.toml
    - Add httpx for HTTP client
    - Add any additional dependencies needed
    - Keep dependencies minimal and focused
    - _Requirements: 8.4_