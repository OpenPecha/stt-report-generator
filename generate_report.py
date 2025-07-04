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
import matplotlib.pyplot as plt
import numpy as np

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
# Visualization Functions
#------------------------------------------------------------------------------

def generate_visualizations(summary_df, output_dir=OUTPUT_DIR):
    """Generate bar and pie charts for each audio file
    
    Args:
        summary_df: DataFrame with summarized data by original_id
        output_dir: Directory to save the visualization files
    """
    try:
        logger.info("Generating visualizations...")
        
        # Create a visualizations directory
        vis_dir = os.path.join(output_dir, "visualizations")
        os.makedirs(vis_dir, exist_ok=True)
        
        # Generate overview charts
        generate_overview_charts(summary_df, vis_dir)
        
        # Generate individual audio file charts for all files
        # Sort by total duration for better organization
        all_files = summary_df.sort_values('total_duration_min', ascending=False)
        
        for _, row in all_files.iterrows():
            generate_audio_file_charts(row, vis_dir)
            
        logger.info(f"Visualizations saved to {vis_dir}")
        
        # Generate HTML index for easy viewing
        generate_visualization_index(all_files, vis_dir)
        
    except Exception as e:
        logger.error(f"Visualization generation failed: {e}")
        raise

def generate_overview_charts(summary_df, vis_dir):
    """Generate overview charts showing all files"""
    # Handle the overview visualization differently based on number of files
    file_count = len(summary_df)
    
    # For the top files by duration (for the main overview)
    top_count = min(30, file_count)  # Show at most 30 files in the overview chart
    plot_df = summary_df.sort_values('total_duration_min', ascending=False).head(top_count)
    
    # Create stacked bar chart for top files
    plt.figure(figsize=(18, 10))  # Wider figure for more files
    
    bar_width = 0.8
    labels = plot_df['original_id']
    
    # Create the stacked bars
    plt.bar(labels, plot_df['submitted_duration_min'], bar_width, 
            label='Submitted', color='#4CAF50')
    plt.bar(labels, plot_df['transcribing_duration_min'], bar_width, 
            bottom=plot_df['submitted_duration_min'], label='Transcribing', color='#2196F3')
    plt.bar(labels, plot_df['trashed_duration_min'], bar_width,
            bottom=plot_df['submitted_duration_min'] + plot_df['transcribing_duration_min'], 
            label='Trashed', color='#F44336')
    
    plt.xlabel('Audio File ID')
    plt.ylabel('Duration (minutes)')
    plt.title(f'Top {top_count} Audio Files by Transcription Status (Total: {file_count} files)')
    plt.xticks(rotation=90, ha='center', fontsize=8)  # Vertical labels for better space usage
    plt.legend()
    plt.tight_layout()
    
    # If we have many files, create additional charts with different groupings
    if file_count > 30:
        # Create a second chart showing files by groups (batches of 30)
        total_batches = (file_count + 29) // 30  # Ceiling division
        
        for batch in range(total_batches):
            if batch == 0:  # Skip first batch as it's already shown in main chart
                continue
                
            start_idx = batch * 30
            end_idx = min((batch + 1) * 30, file_count)
            
            batch_df = summary_df.sort_values('total_duration_min', ascending=False).iloc[start_idx:end_idx]
            
            # Skip if no files in this batch (shouldn't happen but just in case)
            if len(batch_df) == 0:
                continue
                
            plt.figure(figsize=(18, 10))
            
            labels = batch_df['original_id']
            
            # Create the stacked bars
            plt.bar(labels, batch_df['submitted_duration_min'], bar_width, 
                    label='Submitted', color='#4CAF50')
            plt.bar(labels, batch_df['transcribing_duration_min'], bar_width, 
                    bottom=batch_df['submitted_duration_min'], label='Transcribing', color='#2196F3')
            plt.bar(labels, batch_df['trashed_duration_min'], bar_width,
                    bottom=batch_df['submitted_duration_min'] + batch_df['transcribing_duration_min'], 
                    label='Trashed', color='#F44336')
            
            plt.xlabel('Audio File ID')
            plt.ylabel('Duration (minutes)')
            plt.title(f'Audio Files {start_idx+1}-{end_idx} by Transcription Status (Batch {batch+1} of {total_batches})')
            plt.xticks(rotation=90, ha='center', fontsize=8)  # Vertical labels for better space usage
            plt.legend()
            plt.tight_layout()
            
            # Save the batch chart
            batch_file = os.path.join(vis_dir, f'overview_duration_batch_{batch+1}.png')
            plt.savefig(batch_file)
            plt.close()
    
    # Save the chart
    overview_file = os.path.join(vis_dir, 'overview_duration.png')
    plt.savefig(overview_file)
    plt.close()
    
    # Create a pie chart for overall status
    plt.figure(figsize=(10, 10))
    
    # Aggregate data for pie chart
    total_submitted = summary_df['submitted_duration_min'].sum()
    total_transcribing = summary_df['transcribing_duration_min'].sum()
    total_trashed = summary_df['trashed_duration_min'].sum()
    
    sizes = [total_submitted, total_transcribing, total_trashed]
    labels = ['Submitted', 'Transcribing', 'Trashed']
    colors = ['#4CAF50', '#2196F3', '#F44336']
    explode = (0.1, 0, 0)  # explode the 1st slice (Submitted)
    
    plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
            shadow=True, startangle=140)
    plt.axis('equal')  # Equal aspect ratio ensures the pie chart is circular.
    plt.title('Overall Transcription Status (by duration)')
    
    # Save the chart
    overview_pie_file = os.path.join(vis_dir, 'overall_status_pie.png')
    plt.savefig(overview_pie_file)
    plt.close()

def generate_audio_file_charts(row, vis_dir):
    """Generate charts for an individual audio file
    
    Args:
        row: Series containing the data for one audio file
        vis_dir: Directory to save visualization files
    """
    original_id = row['original_id']
    
    # Create a directory for this file's visualizations
    file_vis_dir = os.path.join(vis_dir, original_id)
    os.makedirs(file_vis_dir, exist_ok=True)
    
    # Create bar chart comparing counts and durations
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Count data
    categories = ['Submitted', 'Transcribing', 'Trashed']
    counts = [row['submitted_count'], row['transcribing_count'], row['trashed_count']]
    colors = ['#4CAF50', '#2196F3', '#F44336']
    
    # Duration data
    durations = [row['submitted_duration_min'], row['transcribing_duration_min'], row['trashed_duration_min']]
    
    # Create the bar charts
    ax1.bar(categories, counts, color=colors)
    ax1.set_title(f'{original_id} - Segment Counts')
    ax1.set_ylabel('Number of Segments')
    
    ax2.bar(categories, durations, color=colors)
    ax2.set_title(f'{original_id} - Duration (minutes)')
    ax2.set_ylabel('Duration (minutes)')
    
    # Add count labels on top of the bars
    for i, v in enumerate(counts):
        ax1.text(i, v + 0.5, str(v), ha='center')
        
    for i, v in enumerate(durations):
        ax2.text(i, v + 0.5, f'{v:.1f}', ha='center')
    
    plt.tight_layout()
    
    # Save the chart
    bar_file = os.path.join(file_vis_dir, f'{original_id}_bars.png')
    plt.savefig(bar_file)
    plt.close()
    
    # Create pie charts for counts and durations
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
    
    # Only include non-zero values in pie charts
    count_labels = []
    count_sizes = []
    count_colors = []
    
    for i, (category, count) in enumerate(zip(categories, counts)):
        if count > 0:
            count_labels.append(category)
            count_sizes.append(count)
            count_colors.append(colors[i])
    
    dur_labels = []
    dur_sizes = []
    dur_colors = []
    
    for i, (category, duration) in enumerate(zip(categories, durations)):
        if duration > 0:
            dur_labels.append(category)
            dur_sizes.append(duration)
            dur_colors.append(colors[i])
    
    # Create the pie charts
    if sum(count_sizes) > 0:
        ax1.pie(count_sizes, labels=count_labels, colors=count_colors, autopct='%1.1f%%',
                shadow=True, startangle=90)
        ax1.set_title(f'{original_id} - Segment Counts')
    else:
        ax1.text(0.5, 0.5, 'No data', ha='center', va='center')
        
    if sum(dur_sizes) > 0:
        ax2.pie(dur_sizes, labels=dur_labels, colors=dur_colors, autopct='%1.1f%%',
                shadow=True, startangle=90)
        ax2.set_title(f'{original_id} - Duration Distribution')
    else:
        ax2.text(0.5, 0.5, 'No data', ha='center', va='center')
    
    plt.tight_layout()
    
    # Save the chart
    pie_file = os.path.join(file_vis_dir, f'{original_id}_pies.png')
    plt.savefig(pie_file)
    plt.close()
    
    return [bar_file, pie_file]

def generate_visualization_index(all_files, vis_dir):
    """Generate an HTML index page to easily view all visualizations
    
    Args:
        all_files: DataFrame containing all files that were visualized
        vis_dir: Directory where visualizations are stored
    """
    # Using double curly braces to escape them in the CSS part
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>STT Transcription Visualizations</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        .overview {{ margin-bottom: 30px; }}
        .batch-charts {{ margin-bottom: 30px; }}
        .file-section {{ margin-bottom: 40px; border-bottom: 1px solid #ccc; padding-bottom: 20px; }}
        img {{ max-width: 100%; margin: 10px 0; box-shadow: 0 0 5px rgba(0,0,0,0.2); }}
        .timestamp {{ color: #666; font-size: 0.8em; }}
        .nav-links {{ margin: 20px 0; }}
        .nav-links a {{ margin-right: 15px; padding: 5px 10px; background-color: #f0f0f0; text-decoration: none; color: #333; border-radius: 3px; }}
        .nav-links a:hover {{ background-color: #ddd; }}
    </style>
</head>
<body>
    <h1>STT Transcription Visualizations</h1>
    <p class="timestamp">Generated on: {timestamp}</p>
    
    <div class="nav-links">
        <a href="#overview">Overview Charts</a>
        {batch_nav}
        <a href="#individual">Individual Files</a>
    </div>
    
    <div id="overview" class="overview">
        <h2>Overview Charts</h2>
        <img src="overview_duration.png" alt="Overall Audio Duration by Status">
        <img src="overall_status_pie.png" alt="Overall Status Distribution">
    </div>
    
    {batch_sections}
    
    <h2 id="individual">Individual Audio Files</h2>
    {file_sections}
</body>
</html>
"""
    file_count = len(all_files)
    batch_nav = ""
    batch_sections = ""
    
    # Generate batch navigation and sections if we have multiple batches
    if file_count > 30:
        total_batches = (file_count + 29) // 30  # Ceiling division
        
        # Create batch navigation links
        for batch in range(1, total_batches):
            batch_nav += f'<a href="#batch{batch+1}">Batch {batch+1}</a>'
        
        # Create batch sections
        for batch in range(1, total_batches):
            batch_sections += f"""
    <div id="batch{batch+1}" class="batch-charts">
        <h2>Batch {batch+1} Charts (Files {batch*30+1}-{min((batch+1)*30, file_count)})</h2>
        <img src="overview_duration_batch_{batch}.png" alt="Batch {batch} Audio Duration by Status">
    </div>
"""
    
    # Create file index for better navigation
    file_index = generate_file_index(all_files)
    
    # Generate individual file sections
    file_sections = ""
    for _, row in all_files.iterrows():
        original_id = row['original_id']
        file_sections += f"""
    <div id="file-{original_id}" class="file-section">
        <h3>{original_id}</h3>
        <p>Total Duration: {row['total_duration_min']:.2f} minutes, Total Segments: {row['total_segments']}</p>
        <img src="{original_id}/{original_id}_bars.png" alt="{original_id} Bar Charts">
        <img src="{original_id}/{original_id}_pies.png" alt="{original_id} Pie Charts">
    </div>
"""
    
    # Fill in the template
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_content = html_content.format(
        timestamp=timestamp, 
        batch_nav=batch_nav,
        batch_sections=batch_sections,
        file_sections=file_index + file_sections)
    
    # Save the HTML file
    index_file = os.path.join(vis_dir, 'index.html')
    with open(index_file, 'w') as f:
        f.write(html_content)
    
    return index_file

def generate_file_index(all_files):
    """Generate an HTML file index for easier navigation
    
    Args:
        all_files: DataFrame containing all files that were visualized
        
    Returns:
        HTML string containing the file index
    """
    # Sort files by total duration
    sorted_files = all_files.sort_values('total_duration_min', ascending=False)
    
    # Create an alphabetical index in columns
    file_count = len(sorted_files)
    
    # Create alphabetical index
    index_html = """<div class="file-index">
    <h3>Quick File Navigation</h3>
    <p>Click on a file ID to jump to its visualizations:</p>
    <div style="column-count: 3; column-gap: 20px;">
"""
    
    # Group files by first character for easier navigation
    first_chars = sorted(set(file_id[0].upper() for file_id in sorted_files['original_id']))
    
    for char in sorted(first_chars):
        char_files = [file_id for file_id in sorted_files['original_id'] if file_id[0].upper() == char]
        if char_files:
            index_html += f"<div><strong>{char}</strong><ul>"
            for file_id in sorted(char_files):
                duration = sorted_files.loc[sorted_files['original_id'] == file_id, 'total_duration_min'].iloc[0]
                index_html += f"<li><a href=\"#file-{file_id}\">{file_id}</a> ({duration:.1f} min)</li>"
            index_html += "</ul></div>"
    
    index_html += """    </div>
</div>
<hr>
"""
    
    return index_html

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
        
        # Generate visualizations
        generate_visualizations(original_summary, OUTPUT_DIR)
        
        logger.info("Report generation completed successfully")
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise

#------------------------------------------------------------------------------
# Script Entry Point
#------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
