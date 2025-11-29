#!/usr/bin/env python3
"""
Complete System Setup Script
Initializes the Meta Ads Analytics Dashboard system from scratch.
"""

import sys
import os
import subprocess
import sqlite3
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


def run_command(command: str, description: str) -> bool:
    """Run a shell command and return success status."""
    logger.info(f"🔄 {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        logger.info(f"✅ {description} - Success")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} - Failed: {e.stderr}")
        return False


def check_prerequisites() -> bool:
    """Check if all prerequisites are installed."""
    logger.info("🔍 Checking prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 13):
        logger.error("❌ Python 3.13+ is required")
        return False
    logger.info("✅ Python version OK")
    
    # Check if uv is installed
    if not run_command("uv --version", "Checking UV package manager"):
        logger.error("❌ UV package manager not found. Install from: https://docs.astral.sh/uv/")
        return False
    
    return True


def setup_environment() -> bool:
    """Setup the development environment."""
    logger.info("🏗️ Setting up environment...")
    
    # Install dependencies
    if not run_command("uv sync", "Installing dependencies"):
        return False
    
    # Check if .env file exists
    env_file = PROJECT_ROOT / ".env"
    env_example = PROJECT_ROOT / ".env.example"
    
    if not env_file.exists() and env_example.exists():
        logger.info("📝 Creating .env file from template")
        env_file.write_text(env_example.read_text())
        logger.warning("⚠️  Please edit .env file with your Meta API access tokens")
    
    return True


def initialize_database() -> bool:
    """Initialize the SQLite database."""
    logger.info("🗄️ Initializing database...")
    
    # Create data directory
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    
    # Run database initialization
    init_script = PROJECT_ROOT / "scripts" / "init_database.py"
    if not run_command(f"uv run python {init_script}", "Setting up database schema"):
        return False
    
    return True


def generate_dashboards() -> bool:
    """Generate dashboard notebooks."""
    logger.info("📊 Generating dashboard notebooks...")
    
    gen_script = PROJECT_ROOT / "scripts" / "generate_dashboards.py"
    if not run_command(f"uv run python {gen_script}", "Generating dashboard notebooks"):
        return False
    
    return True


def verify_setup() -> bool:
    """Verify the setup is working correctly."""
    logger.info("🔍 Verifying setup...")
    
    # Check database
    db_path = PROJECT_ROOT / "data" / "meta_ads.db"
    if not db_path.exists():
        logger.error("❌ Database file not found")
        return False
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM data_job_types")
            job_count = cursor.fetchone()[0]
            logger.info(f"✅ Database OK - {job_count} job types configured")
    except Exception as e:
        logger.error(f"❌ Database verification failed: {e}")
        return False
    
    # Check notebooks
    notebooks_dir = PROJECT_ROOT / "notebooks"
    dashboard_files = list(notebooks_dir.glob("*_dashboard.py"))
    logger.info(f"✅ Notebooks OK - {len(dashboard_files)} dashboards generated")
    
    # Test notebook syntax
    index_notebook = notebooks_dir / "index.py"
    if not run_command(f"uv run marimo check {index_notebook}", "Validating notebook syntax"):
        return False
    
    return True


def print_next_steps():
    """Print instructions for next steps."""
    logger.info("🎉 Setup completed successfully!")
    
    print("\n" + "="*60)
    print("🚀 NEXT STEPS")
    print("="*60)
    
    print("\n1. 📝 Configure Meta API Tokens:")
    print("   Edit .env file with your Meta access tokens")
    print("   META_ACCESS_TOKENS=token1,token2,token3,token4")
    
    print("\n2. 🔄 Start Data Extraction Service:")
    print("   uv run uvicorn app.main:app --reload --port 8000")
    
    print("\n3. 📊 Launch Analytics Dashboard:")
    print("   uv run marimo run notebooks/index.py --port 2718")
    
    print("\n4. 🌐 Access Your Dashboards:")
    print("   • Analytics: http://localhost:2718")
    print("   • API Docs: http://localhost:8000/docs")
    
    print("\n5. 📥 Extract Your Data:")
    print("   curl -X POST http://localhost:8000/api/v1/extract \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"account_ids\": [\"YOUR_ACCOUNT_ID\"], \"start_date\": \"2024-01-01\", \"end_date\": \"2024-01-31\"}'")
    
    print("\n📚 Documentation:")
    print("   • README.md - Main documentation")
    print("   • notebooks/README.md - Dashboard development guide")
    print("   • http://localhost:8000/docs - API documentation (when running)")
    
    print("\n" + "="*60)


def main():
    """Main setup function."""
    print("🚀 Meta Ads Analytics Dashboard - System Setup")
    print("="*60)
    
    try:
        # Check prerequisites
        if not check_prerequisites():
            sys.exit(1)
        
        # Setup environment
        if not setup_environment():
            sys.exit(1)
        
        # Initialize database
        if not initialize_database():
            sys.exit(1)
        
        # Generate dashboards
        if not generate_dashboards():
            sys.exit(1)
        
        # Verify setup
        if not verify_setup():
            sys.exit(1)
        
        # Print next steps
        print_next_steps()
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Setup failed with unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()