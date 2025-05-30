#!/bin/bash
# cleanup_for_github.sh - Remove development artifacts for clean GitHub repo

echo "🧹 Cleaning up project for GitHub release..."

# Remove development/testing scripts
echo "Removing development scripts..."
rm -f cli_mvp.py
rm -f create_project_handoff.py
rm -f diagnostic_tests.py
rm -f emergency_extraction.py
rm -f employer_demo.py
rm -f enhanced_chamber_extraction.py
rm -f final_validation.py
rm -f fix_installation.py
rm -f integration_test.py
rm -f integration_tests.py
rm -f prove_production_ready.py
rm -f quick_real_test.py
rm -f quick_test.py
rm -f test_chamber_integration.py
rm -f test_scraper_fixes.py
rm -f test_without_llm.py
rm -f validate_fixes.py
rm -f run_tests.py
rm -f make_executable.sh
rm -f reset_db.sh

# Remove excess documentation (over-engineered)
echo "Removing excess documentation..."
rm -f ARCHITECTURE.md
rm -f CONTRIBUTING.md
rm -f DEV_DOCUMENTATION.md
rm -f IMPLEMENTATION_COMPLETE.md
rm -f PRODUCTION_CHECKLIST.md
rm -f PROJECT_HANDOFF_DOCUMENT.md
rm -f PROJECT_STATUS.md
rm -f ROADMAP.md
rm -f TROUBLESHOOTING.md

# Remove development data/artifacts
echo "Removing development artifacts..."
rm -f test_results.csv
rm -rf .pytest_cache/
rm -rf .qodo/
rm -rf logs/
rm -rf my_custom_temp_logs/
rm -rf my_test_data_dir_from_env/
rm -rf reports/

# Clean up data directory (keep structure, remove files)
echo "Cleaning data directory..."
find data/ -name "*.db" -delete 2>/dev/null || true
find data/ -name "*.sqlite*" -delete 2>/dev/null || true
find data/ -name "*.csv" -delete 2>/dev/null || true
find data/ -name "*.log" -delete 2>/dev/null || true

# Remove system files
echo "Removing system files..."
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo "✅ Cleanup complete!"
echo ""
echo "Files remaining for GitHub:"
echo "📁 Core project files:"
echo "  - README.md, LICENSE, requirements.txt"
echo "  - setup.sh, cli.py"  
echo "  - lead_gen_pipeline/ (source code)"
echo "  - tests/ (test suite)"
echo "  - Dockerfile, docker-compose.yml"
echo ""
echo "📁 Promotional materials moved to _promotional/:"
ls -la _promotional/ 2>/dev/null || echo "  (promotional folder not found)"
echo ""
echo "🚀 Ready for GitHub release!"
