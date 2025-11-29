# 📊 Marimo Analytics Dashboards

Interactive dashboard system built with Marimo notebooks for Meta Ads analytics.

## 🏗️ Structure

```
notebooks/
├── index.py                      # 🏠 Main navigation dashboard
├── ad_performance_dashboard.py   # 📈 Campaign performance analytics
├── campaign_analytics_dashboard.py # 📊 Conversion & ROAS analysis
├── audience_insights_dashboard.py  # 👥 Demographic analytics
├── utils/
│   ├── db_connection.py          # Database connection management
│   ├── common.py                 # Shared UI components
│   ├── template_generator.py     # Dashboard template system
│   ├── dashboard_factory.py      # Auto-generation utilities
│   └── error_handler.py          # Error handling utilities
└── README.md
```

## 🚀 Quick Start

### 1. Setup System
```bash
# Initialize database and generate dashboards
uv run python scripts/init_database.py
uv run python scripts/generate_dashboards.py
```

### 2. Launch Dashboards
```bash
# Start main navigation dashboard
uv run marimo run notebooks/index.py --port 2718

# Or edit mode for development
uv run marimo edit notebooks/index.py
```

### 3. Access Analytics
- **Main Dashboard**: http://localhost:2718
- **Account Selection**: Choose account from dropdown
- **Navigate**: Click dashboard cards to access analytics

## 📊 Dashboard Features

### 🏠 Index Dashboard (`index.py`)
- **Multi-tenant Navigation**: Account selection and filtering
- **Dynamic Discovery**: Automatically detects available dashboards
- **System Status**: Database connectivity and data availability
- **Dashboard Management**: Generation and refresh utilities

### 📈 Analytics Dashboards
- **Interactive KPIs**: Real-time metrics with formatting
- **Time Series Charts**: Trend analysis with date filtering
- **Performance Comparisons**: Campaign and ad set analysis
- **Data Tables**: Sortable, filterable detailed views
- **Error Handling**: Graceful degradation and user feedback

### 🔧 Auto-Generated Dashboards
- **Template-Based**: Consistent UI patterns across all dashboards
- **Schema-Aware**: Adapts to table structure automatically
- **Extensible**: Easy to add new job types and visualizations

## 🛠️ Development

### Adding New Dashboard Types
```bash
# 1. Add job type to database
sqlite3 data/meta_ads.db "INSERT INTO data_job_types (job_type_id, job_name, description, table_name, is_active) VALUES ('new_analytics', 'New Analytics', 'Description', 'new_data_table', 1);"

# 2. Create data table
sqlite3 data/meta_ads.db "CREATE TABLE new_data_table (id INTEGER PRIMARY KEY, account_id TEXT, date_start DATE, ...);"

# 3. Auto-generate dashboard
uv run python scripts/generate_dashboards.py

# 4. Dashboard automatically appears in index
```

### Customizing Templates
- **Edit**: `notebooks/utils/template_generator.py`
- **Regenerate**: `uv run python scripts/generate_dashboards.py`
- **Test**: `uv run marimo run notebooks/index.py`

### Shared Utilities
- **`db_connection.py`**: Database queries and connection management
- **`common.py`**: UI components, formatting, navigation
- **`template_generator.py`**: Dashboard template system
- **`dashboard_factory.py`**: Auto-generation and discovery
- **`error_handler.py`**: Consistent error handling

## 🔍 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **No dashboards showing** | Run `uv run python scripts/generate_dashboards.py` |
| **Database connection error** | Check `data/meta_ads.db` exists, run `scripts/init_database.py` |
| **No data in dashboards** | Extract data via FastAPI service first |
| **Dashboard generation fails** | Check job types in `data_job_types` table |
| **Import errors** | Run `uv sync` to install dependencies |

### Debug Commands
```bash
# Test database connection
sqlite3 data/meta_ads.db ".tables"

# Check dashboard registry
uv run python -c "from notebooks.utils.dashboard_factory import dashboard_factory; print(dashboard_factory.get_dashboard_registry())"

# Validate notebook syntax
uv run marimo check notebooks/index.py
```

## 📚 Architecture Notes

- **Reactive Notebooks**: Marimo automatically updates cells when dependencies change
- **Multi-tenant**: All queries filter by `account_id` for security
- **Template System**: New dashboards generated automatically from database schema
- **Error Handling**: Graceful degradation with user-friendly messages