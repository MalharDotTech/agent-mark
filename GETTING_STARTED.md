# 🚀 Getting Started

Quick start guide for the Meta Ads Analytics Dashboard system.

## 📋 Prerequisites

- **Python 3.13+** - Modern Python version
- **UV Package Manager** - Fast Python package installer ([Install UV](https://docs.astral.sh/uv/))
- **Meta Developer Account** - With advertising API access tokens

## ⚡ Quick Setup (5 minutes)

### 1. Clone and Setup
```bash
git clone <repository>
cd meta-ads-analytics

# Complete system setup (database, dashboards, dependencies)
uv run python scripts/setup_system.py
```

### 2. Configure API Tokens
```bash
# Edit .env file with your Meta API tokens
nano .env

# Add your tokens:
META_ACCESS_TOKENS=token1,token2,token3,token4
```

### 3. Start Services
```bash
# Terminal 1: Start data extraction API
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2: Start analytics dashboard
uv run marimo run notebooks/index.py --port 2718
```

### 4. Access Your Dashboard
- **Analytics Dashboard**: http://localhost:2718
- **API Documentation**: http://localhost:8000/docs

## 📊 First Data Extraction

### Via API
```bash
curl -X POST http://localhost:8000/api/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "account_ids": ["YOUR_ACCOUNT_ID"],
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }'
```

### Via Dashboard
1. Go to http://localhost:2718
2. Select your account from the dropdown
3. Click on dashboard cards to view analytics
4. Use filters to customize date ranges and metrics

## 🎯 What You Get

### 📈 Interactive Dashboards
- **Ad Performance**: Campaign metrics, spend analysis, KPIs
- **Campaign Analytics**: Conversion tracking, ROAS analysis  
- **Audience Insights**: Demographic and behavioral data
- **Auto-generated**: New dashboards for any data type you add

### 🔄 Automated System
- **Template-based**: Consistent dashboard generation
- **Multi-tenant**: Account-based data isolation
- **Extensible**: Easy to add new data types and visualizations

### 🛠️ Developer-Friendly
- **FastAPI**: Modern Python web framework with auto-docs
- **SQLite**: Lightweight database, no setup required
- **Marimo**: Reactive notebooks for interactive analytics

## 📚 Next Steps

### Learn the System
- **[README.md](README.md)** - Complete feature overview
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development guide and patterns
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture details

### Customize Your Setup
- **Add new dashboard types**: Follow the guide in DEVELOPMENT.md
- **Customize visualizations**: Edit dashboard templates
- **Extend API**: Add new endpoints for custom data sources

### Deploy to Production
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide
- **Security**: Multi-tenant isolation and API token management
- **Monitoring**: Health checks and logging configuration

## 🔍 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **No dashboards showing** | Run `uv run python scripts/generate_dashboards.py` |
| **Database errors** | Check `data/meta_ads.db` exists, run setup script |
| **No data in dashboards** | Extract data via API first |
| **Import errors** | Run `uv sync` to install dependencies |

### Debug Commands
```bash
# Check system health
uv run python scripts/generate_dashboards.py

# Test database
sqlite3 data/meta_ads.db ".tables"

# Validate notebooks
uv run marimo check notebooks/index.py
```

### Get Help
- **Check logs**: Look for error messages in terminal output
- **API docs**: Visit http://localhost:8000/docs for API reference
- **Database**: Use `sqlite3 data/meta_ads.db` to inspect data

## 🎉 Success Indicators

You'll know everything is working when:

✅ **Setup script completes** without errors  
✅ **Dashboard shows** at http://localhost:2718  
✅ **API docs load** at http://localhost:8000/docs  
✅ **Database has tables**: `sqlite3 data/meta_ads.db ".tables"`  
✅ **Dashboards generate**: Multiple `*_dashboard.py` files in `notebooks/`  

## 🚀 Ready to Scale?

Once you're comfortable with the basics:

- **Add more data types** by inserting into `data_job_types` table
- **Customize dashboard templates** in `notebooks/utils/template_generator.py`
- **Deploy to production** following the deployment guide
- **Monitor and maintain** using the provided scripts and documentation

---

**Welcome to your new Meta Ads Analytics platform!** 🎊