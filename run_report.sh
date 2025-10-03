#!/bin/bash
# Script to run STT report generator and SRT file generator

# Path to the project directory
PROJECT_DIR="/home/gangagyatso/Desktop/stt-report-generator"

# Activate virtual environment if you're using one
source "$PROJECT_DIR/venv/bin/activate"

# Change to the project directory
cd "$PROJECT_DIR"

# Step 1: Run the report generator
echo "Running report generator..."
python generate_report.py

# Step 2: Run the SRT file generator
echo "Running SRT file generator..."
python generate_srt_files.py

# Echo completion message
echo "Both report and SRT file generation completed."

# Optional: Push to GitHub (uncomment if needed)
# git add reports/
# git commit -m "📊 Weekly STT report update and SRT files $(date +%Y-%m-%d)"
# git push
