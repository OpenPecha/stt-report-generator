#!/bin/bash
# Script to run STT report generator

# Path to the project directory
PROJECT_DIR="/home/gangagyatso/Desktop/stt-report-generator"

# Activate virtual environment if you're using one
source "$PROJECT_DIR/venv/bin/activate"

# Change to the project directory
cd "$PROJECT_DIR"

# Run the report generator
python generate_report.py

# Optional: Push to GitHub (uncomment if needed)
# git add reports/
# git commit -m "📊 Weekly STT report update $(date +%Y-%m-%d)"
# git push
