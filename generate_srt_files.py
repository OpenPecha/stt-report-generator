#!/usr/bin/env python3
"""
STT SRT File Generator
--------------------
This script generates SRT subtitle files from transcription data for audio files
where transcribing_count = 0, meaning no segments are currently being transcribed.
SRT files can be generated even if some segments are still in submitted state.

The script uses reviewed_transcript when available, falling back to transcript
for segments that haven't been reviewed yet. It never uses inference_transcript.

The script can be run standalone or integrated with the report generation workflow.
"""

# Standard library imports
import os
import sys
import logging
from datetime import timedelta
from pathlib import Path

# Third-party imports
import pandas as pd

# Add project root to path for relative imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

#------------------------------------------------------------------------------
# Configuration
#------------------------------------------------------------------------------

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("stt-srt-generator")

# Constants
OUTPUT_DIR = "reports"  # Same as generate_report.py
SRT_OUTPUT_DIR = "srt_output"  # Default SRT output subdirectory

#------------------------------------------------------------------------------
# Helper Functions
#------------------------------------------------------------------------------

def milliseconds_to_srt_time(ms):
    """Convert milliseconds to SRT time format (HH:MM:SS,mmm)"""
    t = timedelta(milliseconds=ms)
    hours, remainder = divmod(t.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{t.microseconds//1000:03}"

def extract_timing_from_filename(filename):
    """Extract start and end timestamps from filename
    Handles different filename formats:
    - STT_GR_XXXX_YYYY_STARTMS_to_ENDMS
    - STT_GR_XXXX_YYYY_ZZ_STARTMS_to_ENDMS
    """
    parts = filename.split('_')
    
    # Find the index of 'to' which separates start and end times
    try:
        to_index = parts.index('to')
        
        # Start ms is the element before 'to'
        start_ms = int(parts[to_index - 1])
        
        # End ms is the element after 'to'
        end_ms = int(parts[to_index + 1])
        
        return start_ms, end_ms
    except (ValueError, IndexError) as e:
        logger.error(f"Failed to extract timing from filename: {filename}, error: {str(e)}")
        return 0, 0

#------------------------------------------------------------------------------
# SRT File Generation
#------------------------------------------------------------------------------

def ensure_output_directory(output_dir):
    """Create the output directory if it doesn't exist"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Output directory ensured: {output_dir}")
    except Exception as e:
        logger.error(f"Failed to create output directory {output_dir}: {str(e)}")
        raise

def generate_srt_files(breakdown_df=None, transcription_df=None, 
                       breakdown_csv=None, transcription_csv=None, 
                       output_dir=None):
    """Generate SRT files for original IDs with transcribing_count = 0
    
    Args:
        breakdown_df: DataFrame with breakdown data (if provided, CSV not needed)
        transcription_df: DataFrame with transcription data (if provided, CSV not needed)
        breakdown_csv: Path to breakdown CSV file (used if breakdown_df not provided)
        transcription_csv: Path to transcription CSV file (used if transcription_df not provided)
        output_dir: Directory where SRT files will be created (default: reports/srt_output)
    """
    try:
        # Set default output directory if not provided
        if output_dir is None:
            output_dir = os.path.join(OUTPUT_DIR, SRT_OUTPUT_DIR)
            
        # Create output directory if it doesn't exist
        ensure_output_directory(output_dir)
        
        # Load data from dataframes or CSV files
        if breakdown_df is None and breakdown_csv:
            logger.info(f"Reading breakdown data from {breakdown_csv}")
            if not os.path.exists(breakdown_csv):
                raise FileNotFoundError(f"Breakdown CSV file not found: {breakdown_csv}")
            breakdown_df = pd.read_csv(breakdown_csv)
            
        if transcription_df is None and transcription_csv:
            logger.info(f"Reading transcription data from {transcription_csv}")
            if not os.path.exists(transcription_csv):
                raise FileNotFoundError(f"Transcription CSV file not found: {transcription_csv}")
            transcription_df = pd.read_csv(transcription_csv)
            
        if breakdown_df is None or transcription_df is None:
            raise ValueError("Must provide either DataFrames or CSV files for both breakdown and transcription data")
        
        # Validate required columns exist
        required_breakdown_cols = ['original_id', 'transcribing_count', 'submitted_count']
        missing_breakdown_cols = [col for col in required_breakdown_cols if col not in breakdown_df.columns]
        if missing_breakdown_cols:
            raise ValueError(f"Breakdown data missing required columns: {missing_breakdown_cols}")
            
        required_transcription_cols = ['original_id', 'file_name']
        missing_transcription_cols = [col for col in required_transcription_cols if col not in transcription_df.columns]
        if missing_transcription_cols:
            raise ValueError(f"Transcription data missing required columns: {missing_transcription_cols}")
        
        # Filter for original_ids with transcribing_count = 0
        # This allows SRT generation even if some segments are still in submitted state
        eligible_ids = breakdown_df[breakdown_df['transcribing_count'] == 0]['original_id'].tolist()
        
        logger.info(f"Found {len(eligible_ids)} original IDs with transcribing_count = 0")
        
        if not eligible_ids:
            logger.info("No eligible original IDs found for SRT generation")
            return 0
    
        # Group by original_id
        grouped = transcription_df.groupby('original_id')
        
        # Process each eligible original_id
        generated_count = 0
        for original_id in eligible_ids:
            if original_id in grouped.groups:
                group_data = grouped.get_group(original_id)
                
                # Create SRT file
                srt_path = os.path.join(output_dir, f"{original_id}.srt")
                
                # Process entries for this original_id
                try:
                    # First, collect all valid entries to avoid file I/O issues
                    entries = []
                    entry_counter = 1
                    
                    # Extract segment numbers for sorting
                    def extract_segment_number(filename):
                        parts = filename.split('_')
                        # Basic segment number is always at index 3
                        segment_num = parts[3]
                        
                        # Check if there's a sub-segment identifier (like '00', '01')
                        # Typically these would be at index 4 if they exist
                        if len(parts) > 5 and parts[4].isdigit() and len(parts[4]) <= 2:
                            # Create a composite segment identifier
                            return f"{segment_num}_{parts[4]}"
                        else:
                            return segment_num
                    
                    # Sort data by segment number first, then by start time
                    group_data = group_data.copy()  # Create a copy to avoid SettingWithCopyWarning
                    group_data['segment_num'] = group_data['file_name'].apply(extract_segment_number)
                    group_data['start_time'] = group_data['file_name'].apply(lambda x: 
                        extract_timing_from_filename(x)[0] if 'to' in x else 0)
                    
                    # Custom sorting for segment numbers that may include sub-segments
                    def segment_sort_key(seg_num):
                        # Split on underscore if it exists
                        if '_' in str(seg_num):
                            main_part, sub_part = seg_num.split('_')
                            return (int(main_part), int(sub_part))
                        else:
                            return (int(seg_num), 0)
                    
                    # Sort using the custom key function
                    sorted_data = group_data.sort_values(
                        by=['segment_num', 'start_time'],
                        key=lambda x: x.map(segment_sort_key) if x.name == 'segment_num' else x
                    )
                    
                    # Process each entry and track seen segments to avoid duplicates
                    seen_segments = set()
                    for _, row in sorted_data.iterrows():
                        try:
                            # Check if required columns exist
                            if 'segment_num' not in row or 'file_name' not in row:
                                logger.warning(f"Skipping row missing required columns: {row}")
                                continue
                                
                            # Use only segment number to identify duplicates
                            segment_key = row['segment_num']
                            
                            # Skip if this segment has already been processed
                            if segment_key in seen_segments:
                                continue
                            
                            # Mark this segment as seen
                            seen_segments.add(segment_key)
                            
                            start_ms, end_ms = extract_timing_from_filename(row['file_name'])
                            
                            # Convert to SRT format
                            start_time = milliseconds_to_srt_time(start_ms)
                            end_time = milliseconds_to_srt_time(end_ms)
                            
                            # Priority: reviewed_transcript > transcript > skip (don't use inference_transcript)
                            transcript = None
                            if 'reviewed_transcript' in row and not pd.isna(row['reviewed_transcript']) and row['reviewed_transcript']:
                                transcript = row['reviewed_transcript']
                            elif 'transcript' in row and not pd.isna(row['transcript']) and row['transcript']:
                                transcript = row['transcript']
                            
                            if not transcript:
                                logger.warning(f"No reviewed_transcript or transcript for {row['file_name']}, skipping")
                                continue
                            
                            # Create the entry
                            entry = f"{entry_counter}\n{start_time} --> {end_time}\n{transcript}\n\n"
                            entries.append(entry)
                            entry_counter += 1
                        except Exception as e:
                            logger.error(f"Error processing {row.get('file_name', 'unknown file')}: {str(e)}")
                    
                    # Write all entries to the file at once
                    if entries:
                        with open(srt_path, 'w', encoding='utf-8') as srt_file:
                            srt_file.writelines(entries)
                        
                        logger.info(f"Generated SRT file for {original_id} with {len(entries)} entries")
                        generated_count += 1
                    else:
                        logger.warning(f"No valid entries found for {original_id}")
                
                except Exception as e:
                    logger.error(f"Error generating SRT for {original_id}: {str(e)}")
            else:
                logger.warning(f"No transcription data found for {original_id}")
    
        logger.info(f"Generated {generated_count} SRT files out of {len(eligible_ids)} eligible original IDs")
        return generated_count
        
    except Exception as e:
        logger.error(f"SRT file generation failed: {str(e)}")
        raise

#------------------------------------------------------------------------------
# Main Execution
#------------------------------------------------------------------------------

def main():
    """Main function to execute the SRT generation process"""
    try:
        logger.info("Starting STT SRT file generation...")
        
        # Default paths - use the latest files from the reports directory
        breakdown_csv = os.path.join(OUTPUT_DIR, "original_id_breakdown_latest.csv")
        transcription_csv = os.path.join(OUTPUT_DIR, "transcription_data_latest.csv")
        srt_output_dir = os.path.join(OUTPUT_DIR, SRT_OUTPUT_DIR)
        
        # Check if required files exist
        if not os.path.exists(breakdown_csv):
            logger.warning(f"Breakdown file not found: {breakdown_csv}")
            logger.info("SRT generation skipped - no breakdown data available")
            return
            
        if not os.path.exists(transcription_csv):
            logger.warning(f"Transcription file not found: {transcription_csv}")
            logger.info("SRT generation skipped - no transcription data available")
            return
        
        # Generate SRT files
        generate_srt_files(
            breakdown_csv=breakdown_csv,
            transcription_csv=transcription_csv,
            output_dir=srt_output_dir
        )
        
        logger.info("SRT file generation completed successfully")
    except Exception as e:
        logger.error(f"SRT file generation failed: {e}")
        raise

if __name__ == "__main__":
    main()
