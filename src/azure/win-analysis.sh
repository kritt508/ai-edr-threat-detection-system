#!/bin/bash
# Version 1.7.0 - Clean Code & Structured Naming

TARGET=$1
DURATION=${2:-5}
OS_VER=${3:-win11}
FILE_SIZE=${4:-unknown}
URL="http://win.sandbox.npu.world:5000"

if [ -z "$TARGET" ]; then
    echo "Usage: $0 <filename> [duration] [os] [size]"
    exit 1
fi

# Generate systematic filename prefix
TIMESTAMP=$(date +%Y%m%d_%H%M)
FILENAME_ONLY=$(echo "$TARGET" | cut -f 1 -d '.')
BASE_NAME="${TIMESTAMP}_${FILENAME_ONLY}_${OS_VER}_${FILE_SIZE}_${DURATION}s"

echo "[$(date +%s)] Step 1: Executing $TARGET..."
EXEC_RES=$(curl --max-time 15 -s -X POST -H "Content-Type: application/json" -d "{\"file_path\": \"C:/Users/cpe/AppData/Local/Temp/malware_uploads/$TARGET\"}" "$URL/execute")
PID=$(echo "$EXEC_RES" | grep -oE '"main_pid":[0-9]+' | cut -d: -f2)

if [ -z "$PID" ]; then 
    echo "Error: Server response: $EXEC_RES"
    exit 1
fi

echo "[$(date +%s)] Malware started (PID: $PID). Monitoring for $DURATION s..."
sleep $DURATION

echo "[$(date +%s)] Step 2: Terminating and Generating Reports..."
TERM_RES=$(curl --max-time 350 -s -X POST "$URL/terminate/$PID")

LOG_FILE=$(echo "$TERM_RES" | grep -oE '"log_filtered":"[^"]+"' | cut -d'"' -f4)
NET_FILE=$(echo "$TERM_RES" | grep -oE '"net_csv":"[^"]+"' | cut -d'"' -f4)

echo "[$(date +%s)] Step 3: Downloading results..."

# Download Process Log
if [ ! -z "$LOG_FILE" ] && [ "$LOG_FILE" != "null" ]; then
    OUT_LOG="${BASE_NAME}_proc.csv"
    echo ">> Saving: $OUT_LOG"
    curl -s "$URL/download_pcap?filename=$LOG_FILE" --output "$OUT_LOG"
else
    echo "!! Process Log not found."
fi

# Download Network Log
if [ ! -z "$NET_FILE" ] && [ "$NET_FILE" != "null" ]; then
    OUT_NET="${BASE_NAME}_net.csv"
    echo ">> Saving: $OUT_NET"
    curl -s "$URL/download_pcap?filename=$NET_FILE" --output "$OUT_NET"
else
    echo "!! Network Log not found."
fi

echo "[$(date +%s)] Done. Analysis for $TARGET completed."
