#!/bin/bash

# Usage: ./list_files.sh [directory] [output_file]
# Defaults to current directory and outputs to file_list.txt

TARGET_DIR="${1:-.}"
OUTPUT_FILE="${2:-file_list.txt}"

echo "Scanning: $TARGET_DIR"
echo "Output:   $OUTPUT_FILE"

find "$TARGET_DIR" | sort > "$OUTPUT_FILE"

echo "Done! $(wc -l < "$OUTPUT_FILE") entries written to $OUTPUT_FILE"

