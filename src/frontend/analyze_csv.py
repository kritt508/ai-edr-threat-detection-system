import sys
import pandas as pd
import json

# Path of the CSV file sent from n8n
file_path = sys.argv[1]

# Most relevant ProcMon columns for behavioral analysis
RELEVANT_COLUMNS = [
    'Operation', 
    'Path', 
    'Detail'
]

try:
    # Load CSV file
    df = pd.read_csv(file_path, on_bad_lines='skip')

    # Verify if relevant columns exist
    available_columns = [col for col in RELEVANT_COLUMNS if col in df.columns]

    if not available_columns:
        print(json.dumps({"error": "CSV does not contain 'Operation', 'Path', or 'Detail' columns.", "file_path": file_path}))
        sys.exit()

    # Filter DataFrame to include only essential columns
    filtered_df = df[available_columns]

    # Remove rows where all data is null
    filtered_df = filtered_df.dropna(how='all')

    # --- Data Reduction: Condense information to prevent AI token limit overflow ---
    # Count duplicate behaviors (rows)
    event_counts = filtered_df.groupby(available_columns).size().reset_index(name='count')

    # Sort by frequency and select the top 50 unique events
    top_events_df = event_counts.sort_values(by='count', ascending=False).head(50)

    # Convert the condensed DataFrame into a JSON string
    events_json = top_events_df.to_json(orient='records')

    # Prepare final output data
    output = {
        "file_name": file_path.split('/')[-1],
        "total_unique_events": len(event_counts),
        "top_50_events_for_analysis": json.loads(events_json) # Convert back to JSON object for n8n
    }

    # Output result as JSON string to stdout for n8n consumption
    print(json.dumps(output))

except Exception as e:
    print(json.dumps({"error": str(e), "file_path": file_path}))