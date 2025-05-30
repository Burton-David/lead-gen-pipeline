#!/bin/bash
# final_github_cleanup.sh - Comprehensive cleanup for GitHub publication

echo "🧹 Final GitHub Cleanup - Chamber Business Directory Scraper"
echo "==========================================================="

# Create backup directory for removed files
mkdir -p .cleanup_backup
BACKUP_DIR=".cleanup_backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📁 Backup directory created: $BACKUP_DIR"

# Function to safely remove files
safe_remove() {
    local file="$1"
    if [ -f "$file" ]; then
        echo "  Removing: $file"
        mv "$file" "$BACKUP_DIR/"
    elif [ -d "$file" ]; then
        echo "  Removing directory: $file"
        mv "$file" "$BACKUP_DIR/"
    fi
}

# Remove development/test scripts
echo "\n🔧 Removing development scripts..."
safe_remove "cli_mvp.py.removed"
safe_remove "create_project_handoff.py"
safe_remove "diagnostic_tests.py"
safe_remove "emergency_extraction.py"
safe_remove "employer_demo.py"
safe_remove "enhanced_chamber_extraction.py"
safe_remove "final_validation.py"
safe_remove "fix_installation.py"
safe_remove "integration_test.py"
safe_remove "integration_tests.py"
safe_remove "prove_production_ready.py"
safe_remove "quick_real_test.py"
safe_remove "quick_test.py"
safe_remove "test_chamber_integration.py"
safe_remove "test_scraper_fixes.py"
safe_remove "test_without_llm.py"
safe_remove "validate_fixes.py"
safe_remove "run_tests.py"
safe_remove "make_executable.sh"
safe_remove "reset_db.sh"

# Remove excess documentation
echo "\n📚 Removing excess documentation..."
safe_remove "ARCHITECTURE.md"
safe_remove "CONTRIBUTING.md"
safe_remove "DEV_DOCUMENTATION.md"
safe_remove "IMPLEMENTATION_COMPLETE.md"
safe_remove "PRODUCTION_CHECKLIST.md"
safe_remove "PROJECT_HANDOFF_DOCUMENT.md"
safe_remove "PROJECT_STATUS.md"
safe_remove "ROADMAP.md"
safe_remove "TROUBLESHOOTING.md"
safe_remove "CLEANUP_CHECKLIST.md"
safe_remove "cleanup_for_github.sh"

# Remove development artifacts
echo "\n🗑️  Removing development artifacts..."
safe_remove "test_results.csv"
safe_remove ".pytest_cache"
safe_remove ".qodo"
safe_remove "logs"
safe_remove "my_custom_temp_logs"
safe_remove "my_test_data_dir_from_env"
safe_remove "reports"

# Clean data directory while preserving structure
echo "\n🧹 Cleaning data directory..."
if [ -d "data" ]; then
    echo "  Cleaning database files..."
    find data/ -name "*.db" -type f -exec mv {} "$BACKUP_DIR/" \; 2>/dev/null || true
    find data/ -name "*.db-shm" -type f -exec mv {} "$BACKUP_DIR/" \; 2>/dev/null || true
    find data/ -name "*.db-wal" -type f -exec mv {} "$BACKUP_DIR/" \; 2>/dev/null || true
    
    echo "  Cleaning test CSV files..."
    safe_remove "data/leads_mvp.db"
    safe_remove "data/chamber_test.csv"
    safe_remove "data/contact_rich_sites.csv"
    safe_remove "data/quick_test_companies.csv"
    safe_remove "data/real_b2b_companies.csv"
    
    # Keep chamber_urls.csv and urls_seed.csv as examples
    echo "  Keeping example CSV files: chamber_urls.csv, urls_seed.csv"
fi

# Remove system files
echo "\n🖥️  Removing system files..."
find . -name ".DS_Store" -type f -delete 2>/dev/null || true
find . -name "*.pyc" -type f -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove old virtual environments if they exist
safe_remove "venv"
safe_remove ".venv"

echo "\n✅ Cleanup completed!"
echo "\n📊 Final project structure:"
echo "├── README.md"
echo "├── LICENSE"
echo "├── requirements.txt"
echo "├── setup.sh"
echo "├── cli.py"
echo "├── .env.example"
echo "├── .gitignore"
echo "├── pytest.ini"
echo "├── Dockerfile"
echo "├── docker-compose.yml"
echo "├── lead_gen_pipeline/"
echo "├── tests/"
echo "├── data/"
echo "│   ├── chamber_urls.csv (example)"
echo "│   └── urls_seed.csv (example)"
echo "└── _promotional/ (excluded from git)"

echo "\n🚀 Ready for GitHub publication!"
echo "\nNext steps:"
echo "1. git init"
echo "2. git add ."
echo "3. git commit -m 'Initial commit: Chamber Business Directory Scraper'"
echo "4. Create GitHub repository"
echo "5. git remote add origin <your-repo-url>"
echo "6. git push -u origin main"

echo "\n💼 Promotional materials are in _promotional/ for your marketing use"
echo "🗂️  Removed files are backed up in: $BACKUP_DIR"
