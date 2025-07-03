#!/usr/bin/env python3
"""
STT Report Generator
--------------------
This script connects to a database, extracts speech-to-text transcription data,
and generates summary reports in markdown and CSV formats.

The reports include statistics such as total transcribed files, audio duration,
and average processing time. Reports are saved with timestamps for historical tracking.
"""

# Standard library imports
import os
import sys
import logging
import re
from datetime import datetime
from pathlib import Path

# Third-party imports
import pandas as pd

# Add project root to path for relative imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Local imports
from util.db_utils import get_sqlalchemy_engine

#------------------------------------------------------------------------------
# Configuration
#------------------------------------------------------------------------------

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("stt-report-generator")

# Constants
OUTPUT_DIR = "reports"
TIMESTAMP_FORMAT = "%Y%m%d"

#------------------------------------------------------------------------------
# Helper Functions
#------------------------------------------------------------------------------

def extract_original_id(segment_id):
    """Extract original file ID from a segment ID
    e.g., STT_GR_0001_0003_22300_to_27800 -> STT_GR_0001
    """
    match = re.match(r'(STT_GR_\d+)_', segment_id)
    if match:
        return match.group(1)
    return segment_id

#------------------------------------------------------------------------------
# Database Functions
#------------------------------------------------------------------------------

def get_database_engine():
    """Create and return a database engine using the utility module"""
    try:
        logger.info("Connecting to database...")
        engine = get_sqlalchemy_engine()
        logger.info("Database connection successful")
        return engine
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def query_transcription_data(engine):
    """Query transcription data from the database
    
    Args:
        engine: SQLAlchemy database engine
        
    Returns:
        DataFrame containing transcription data
    """
    try:
        logger.info("Querying transcription data...")
        
        query = """
            SELECT 
                *
            FROM "Task" t
            WHERE t.group_id in (32, 33)
        """
        
        df = pd.read_sql(query, engine)
        logger.info(f"Query returned {len(df)} records")
        
        # Apply extraction function if file_name column exists
        if 'file_name' in df.columns:
            logger.info("Extracting original IDs from file names...")
            df['original_id'] = df['file_name'].apply(extract_original_id)
            logger.info("Original IDs extracted successfully")
        
        return df
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        raise

#------------------------------------------------------------------------------
# Report Generation Functions
#------------------------------------------------------------------------------
def summarize_by_original_id(df):
    """Summarize count and duration of segments per original_id and state"""

    if 'original_id' not in df.columns or 'state' not in df.columns or 'audio_duration' not in df.columns:
        raise ValueError("Required columns missing in DataFrame")

    grouped = df.groupby(['original_id', 'state'])

    # Count of segments per original_id and state
    count_df = grouped.size().unstack(fill_value=0)

    # Total duration per original_id and state
    duration_df = grouped['audio_duration'].sum().unstack(fill_value=0) / 60  # convert to minutes

    # Combine both
    summary = pd.DataFrame(index=count_df.index)
    summary['transcribing_count'] = count_df.get('transcribing', 0)
    summary['transcribing_duration_min'] = duration_df.get('transcribing', 0).round(2)
    summary['submitted_count'] = count_df.get('submitted', 0)
    summary['submitted_duration_min'] = duration_df.get('submitted', 0).round(2)
    summary['trashed_count'] = count_df.get('trashed', 0)
    summary['trashed_duration_min'] = duration_df.get('trashed', 0).round(2)

    summary['total_segments'] = summary[['transcribing_count', 'submitted_count', 'trashed_count']].sum(axis=1)
    summary['total_duration_min'] = summary[[
        'transcribing_duration_min', 'submitted_duration_min', 'trashed_duration_min'
    ]].sum(axis=1).round(2)

    return summary.reset_index().sort_values('original_id')

def generate_summary_report(df, original_summary):
    """Generate a markdown summary report from transcription data
    
    Args:
        df: DataFrame with transcription data
        original_summary: DataFrame with summarized data by original_id
        
    Returns:
        String containing markdown report
    """
    try:
        logger.info("Generating summary report...")
        
        # Calculate statistics
        stats = {}
        stats['report_date'] = datetime.now().strftime("%Y-%m-%d")
        
        # Date range
        if 'created_at' in df.columns:
            stats['min_date'] = df['created_at'].min().strftime("%Y-%m-%d") if not df.empty else "N/A"
            stats['max_date'] = df['created_at'].max().strftime("%Y-%m-%d") if not df.empty else "N/A"
        else:
            stats['min_date'] = "N/A"
            stats['max_date'] = "N/A"
        
        # Count unique original IDs if available
        if 'original_id' in df.columns:
            stats['total_files'] = df['original_id'].nunique()
        else:
            stats['total_files'] = len(df)
        
        # Calculate total audio duration (assuming in seconds, converting to hours)
        if 'audio_duration' in df.columns:
            total_seconds = df['audio_duration'].sum()
            stats['total_hours'] = total_seconds / 3600  # convert to hours
            stats['avg_duration'] = (total_seconds / 60) / stats['total_files'] if stats['total_files'] > 0 else 0
        else:
            stats['total_hours'] = 0
            stats['avg_duration'] = 0
            
        # Get status counts and durations
        if 'state' in df.columns and 'audio_duration' in df.columns:
            # Counts by state
            state_counts = df['state'].value_counts()
            stats['transcribing_count'] = state_counts.get('transcribing', 0)
            stats['submitted_count'] = state_counts.get('submitted', 0)
            stats['trashed_count'] = state_counts.get('trashed', 0)
            
            # Durations by state
            state_durations = df.groupby('state')['audio_duration'].sum()
            stats['transcribing_duration'] = state_durations.get('transcribing', 0) / 3600  # convert to hours
            stats['submitted_duration'] = state_durations.get('submitted', 0) / 3600  # convert to hours
            stats['trashed_duration'] = state_durations.get('trashed', 0) / 3600  # convert to hours
        
        summary = f"""# STT Transcription Report

## Summary for {stats['report_date']}

- **Date Range**: {stats['min_date']} to {stats['max_date']}
- **Total Transcribed Files**: {stats['total_files']}
- **Total Audio Duration**: {stats['total_hours']:.2f} hours
- **Average File Duration**: {stats['avg_duration']:.2f} minutes

## Status Breakdown

| Status | Count | Duration (hours) |
|--------|-------|------------------|
| Transcribing | {stats.get('transcribing_count', 0)} | {stats.get('transcribing_duration', 0):.2f} |
| Submitted | {stats.get('submitted_count', 0)} | {stats.get('submitted_duration', 0):.2f} |
| Trashed | {stats.get('trashed_count', 0)} | {stats.get('trashed_duration', 0):.2f} |

## Weekly Progress

| Metric | Value |
|--------|-------|
| Completed Transcriptions | {stats['total_files']} |
| Processed Audio | {stats['total_hours']:.2f} hours |
| Avg. Processing Time | {stats['avg_duration']:.2f} minutes |
"""

        # Add original ID summary table if available
        if not original_summary.empty:
            summary += "\n## Original ID Breakdown\n\n"
            summary += "| Original ID | Total Segments | Total Duration (min) | Submitted Count | Submitted Duration (min) | Transcribing Count | Transcribing Duration (min) | Trashed Count | Trashed Duration (min) |\n"
            summary += "|-------------|---------------|----------------------|----------------|--------------------------|-------------------|----------------------------|--------------|--------------------------|\n"
            
            # Add top 10 rows to keep the report concise
            for _, row in original_summary.head(10).iterrows():
                summary += f"| {row['original_id']} | {row['total_segments']} | {row['total_duration_min']} | "
                summary += f"{row['submitted_count']} | {row['submitted_duration_min']:.2f} | "
                summary += f"{row['transcribing_count']} | {row['transcribing_duration_min']:.2f} | "
                summary += f"{row['trashed_count']} | {row['trashed_duration_min']:.2f} |\n"
            
            if len(original_summary) > 10:
                summary += "\n*Note: Only showing top 10 entries. See CSV for complete breakdown.*\n"
        
        logger.info("Summary report generated successfully")
        return summary
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise

#------------------------------------------------------------------------------
# File Operations
#------------------------------------------------------------------------------

def ensure_output_directory(output_dir=OUTPUT_DIR):
    """Create the output directory if it doesn't exist
    
    Args:
        output_dir: Path to the output directory
    """
    Path(output_dir).mkdir(exist_ok=True, parents=True)
    logger.info(f"Ensured output directory exists: {output_dir}")

def save_outputs(df, summary, output_dir=OUTPUT_DIR):
    """Save the dataframe and summary report to files
    
    Args:
        df: DataFrame with transcription data
        summary: String with markdown report
        output_dir: Directory to save the files
    """
    try:
        # Make sure the output directory exists
        ensure_output_directory(output_dir)
        
        # Filter only relevant columns for CSV output as requested
        relevant_columns = [
            'file_name', 'state', 'inference_transcript', 'transcript', 'url',
            'created_at', 'submitted_at', 'reviewed_at', 'audio_duration', 'original_id'
        ]
        
        # Only keep columns that exist in the DataFrame
        csv_columns = [col for col in relevant_columns if col in df.columns]
        filtered_df = df[csv_columns]
        
        # Generate filenames with timestamp
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        csv_file = os.path.join(output_dir, f"transcription_data_{timestamp}.csv")
        report_file = os.path.join(output_dir, f"summary_report_{timestamp}.md")
        
        # Save timestamped files
        logger.info(f"Saving data to {csv_file}")
        filtered_df.to_csv(csv_file, index=False)
        
        logger.info(f"Saving report to {report_file}")
        with open(report_file, "w") as f:
            f.write(summary)
        
        # Also save with standard names for GitHub Actions to commit
        latest_csv = os.path.join(output_dir, "transcription_data_latest.csv")
        latest_report = os.path.join(output_dir, "summary_report_latest.md")
        
        filtered_df.to_csv(latest_csv, index=False)
        with open(latest_report, "w") as f:
            f.write(summary)
            
        logger.info("All outputs saved successfully")
    except Exception as e:
        logger.error(f"Failed to save outputs: {e}")
        raise

#------------------------------------------------------------------------------
# Main Execution
#------------------------------------------------------------------------------

def main():
    """Main function to execute the report generation process"""
    try:
        logger.info("Starting STT report generation...")
        
        # Ensure output directory exists first
        ensure_output_directory()
        
        # Database operations
        engine = get_database_engine()
        df = query_transcription_data(engine)
        
        # Generate per-original_id summary
        original_summary = summarize_by_original_id(df)
        original_summary_file = os.path.join(OUTPUT_DIR, f"original_id_breakdown_{datetime.now().strftime(TIMESTAMP_FORMAT)}.csv")
        original_summary.to_csv(original_summary_file, index=False)

        # Also save latest version for GitHub tracking
        original_summary.to_csv(os.path.join(OUTPUT_DIR, "original_id_breakdown_latest.csv"), index=False)

        # Generate summary report using dataframe and original_summary
        summary = generate_summary_report(df, original_summary)
        
        # File operations
        save_outputs(df, summary)
        
        logger.info("Report generation completed successfully")
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise

#------------------------------------------------------------------------------
# Script Entry Point
#------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
