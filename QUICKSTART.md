# 🚀 Quick Start Guide - Meta Ads Analytics

## For First-Time Setup

### 1. Install Dependencies
```bash
cd /Users/malhar/Code/agent-mark

# UV is already installed, sync dependencies
uv sync
```

### 2. Configure Tokens
The `.env` file is already configured with 4 working tokens:
```bash
# Verify tokens are set
grep META_ACCESS_TOKENS .env | wc -c
# Should show ~800+ characters (4 tokens)
```

### 3. Initialize Database (if needed)
```bash
# Database will auto-create on first run, but you can manually initialize:
rm -f data/meta_ads.db*  # Remove old database
uv run uvicorn app.main:app --port 8000
# Wait for "Application startup complete" then Ctrl+C
```

### 4. Start Services

**Terminal 1 - FastAPI Backend:**
```bash
uv run uvicorn app.main:app --reload --port 8000

# You should see:
# ✅ Database tables created successfully
# ✅ Core services initialized successfully
# ✅ Application startup complete
```

**Terminal 2 - Marimo Dashboards:**
```bash
uv run marimo run notebooks/index.py --port 2718

# Access at: http://localhost:2718
```

---

## For Testing New Features

### Test RNF Extraction
```bash
# Test patterns (doesn't call FastAPI)
uv run python test_rnf_extraction.py

# Expected output:
# ✅ Daily R&F records: 8
# ✅ Campaign R&F records: 16
# ✅ Overlap pairs analyzed: 3
```

### Test Audience Extraction
```bash
# Test patterns (doesn't call FastAPI)
uv run python test_audience_extraction.py

# Expected output:
# ✅ Audience segments extracted
# ✅ Age breakdown: 7 segments
```

### Integration Test (requires running server)
```bash
# Terminal 1: Start server
uv run uvicorn app.main:app --port 8000

# Terminal 2: Run integration test
uv run python test_integration_rnf.py

# Expected output:
# ✅ RNF Cumulative: 8 records
# ✅ Audience Insights: 7 records
# ✅ Integration Test Completed Successfully
```

---

## Extract Data for Your Account

### 1. List Available Accounts
```bash
curl http://localhost:8000/api/v1/accounts | python3 -m json.tool

# Or check validated accounts:
# act_66395971 - Porter - old
# act_547569015598645 - Porter - BM - new (Active)
# act_816491348940413 - Porter Partnerships
```

### 2. Extract RNF Cumulative Data
```bash
curl -X POST http://localhost:8000/api/v1/extract-rnf-cumulative \
  -H "Content-Type: application/json" \
  -d '{
    "account_ids": ["act_547569015598645"],
    "start_date": "2025-12-02",
    "end_date": "2025-12-09",
    "level": "account",
    "time_increment": "1"
  }' | python3 -m json.tool

# Expected:
# {
#   "job_id": "...",
#   "total_records": 8,
#   "accounts_processed": 1
# }
```

### 3. Extract Audience Insights
```bash
curl -X POST http://localhost:8000/api/v1/extract-audience \
  -H "Content-Type: application/json" \
  -d '{
    "account_ids": ["act_547569015598645"],
    "start_date": "2025-12-02",
    "end_date": "2025-12-09",
    "breakdown_types": ["age", "gender"],
    "level": "account"
  }' | python3 -m json.tool

# Expected:
# {
#   "job_id": "...",
#   "total_records": 14,  # 7 age + 7 gender (or combined)
#   "accounts_processed": 1
# }
```

### 4. Retrieve Stored Data
```bash
# Get audience summary
curl "http://localhost:8000/api/v1/audience/act_547569015598645/summary?breakdown_type=age" \
  | python3 -m json.tool

# Expected:
# {
#   "breakdown_type": "age",
#   "summary": [
#     {"breakdown_value": "25-34", "total_reach": 5195724, ...},
#     {"breakdown_value": "18-24", "total_reach": 3549050, ...},
#     ...
#   ]
# }
```

---

## Database Queries

### Check What's Stored
```bash
# Enter SQLite shell
sqlite3 data/meta_ads.db

# Check job types
SELECT * FROM data_job_types;

# Check RNF data
SELECT date_start, reach, frequency FROM rnf_cumulative_data LIMIT 5;

# Check audience data
SELECT breakdown_type, breakdown_value, reach 
FROM audience_insights_data 
ORDER BY reach DESC 
LIMIT 10;

# Exit
.exit
```

### Quick Stats
```bash
# One-liner to check all table counts
sqlite3 data/meta_ads.db "
  SELECT 'ad_performance_data' as table_name, COUNT(*) as count FROM ad_performance_data
  UNION ALL
  SELECT 'rnf_cumulative_data', COUNT(*) FROM rnf_cumulative_data
  UNION ALL
  SELECT 'rnf_overlap_data', COUNT(*) FROM rnf_overlap_data
  UNION ALL
  SELECT 'audience_insights_data', COUNT(*) FROM audience_insights_data;
"
```

---

## Troubleshooting

### Server won't start
```bash
# Check if port is in use
lsof -ti:8000

# Kill existing process
lsof -ti:8000 | xargs kill -9

# Restart
uv run uvicorn app.main:app --port 8000
```

### Database errors
```bash
# Reset database (CAUTION: deletes all data)
rm -f data/meta_ads.db*
uv run uvicorn app.main:app --port 8000
# Database will be recreated
```

### Token issues
```bash
# Verify tokens are loaded
curl http://localhost:8000/health | python3 -m json.tool

# Check logs for token count
grep "Configured with" /tmp/fastapi*.log
# Should show: "Configured with 4 access tokens"
```

### API errors (403, 400)
```bash
# 403 Forbidden: Account not accessible with tokens
# Solution: Use one of the validated accounts:
#   - act_547569015598645 (Porter - BM - new) ✅ RECOMMENDED

# 400 Bad Request: Invalid parameters
# Solution: Check request format in API docs
open http://localhost:8000/docs
```

---

## Development Workflow

### Adding a New Feature
1. Test API pattern with test script
2. Update database schema if needed
3. Add/modify service methods
4. Create/update API endpoints
5. Write integration test
6. Update documentation

### Running All Tests
```bash
# Start server
uv run uvicorn app.main:app --port 8000 &
SERVER_PID=$!

# Run tests
uv run python test_rnf_extraction.py
uv run python test_audience_extraction.py
uv run python test_integration_rnf.py

# Stop server
kill $SERVER_PID
```

---

## Production Checklist

- [ ] Environment variables set correctly
- [ ] Database initialized
- [ ] All tokens validated
- [ ] Health check passes
- [ ] At least one account has data
- [ ] Dashboards load correctly
- [ ] API documentation accessible at `/docs`

---

## Key URLs

| Service | URL | Purpose |
|---------|-----|---------|
| FastAPI Server | http://localhost:8000 | Data extraction API |
| API Docs | http://localhost:8000/docs | Interactive API documentation |
| Health Check | http://localhost:8000/health | System status |
| Marimo Dashboards | http://localhost:2718 | Analytics interface |

---

## Getting Help

1. Check logs: `cat /tmp/fastapi*.log`
2. Review API docs: http://localhost:8000/docs
3. Check database: `sqlite3 data/meta_ads.db ".tables"`
4. Read detailed docs: `ARCHITECTURE.md`, `DEVELOPMENT.md`
5. Review session summary: `SESSION_SUMMARY.md`

