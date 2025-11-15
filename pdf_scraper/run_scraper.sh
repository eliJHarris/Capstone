#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="pdf-scraper"
OUTPUT_DEFAULT="combined.txt"

read -rp "Enter domain or URL to crawl (e.g., example.com or https://example.com): " user_input
user_input="${user_input//[$'\t\r\n ']}"

if [[ -z "$user_input" ]]; then
    echo "No domain provided. Exiting."
    exit 1
fi

if [[ "$user_input" =~ ^https?:// ]]; then
    start_url="$user_input"
else
    start_url="https://$user_input"
fi

read -rp "Output file name [${OUTPUT_DEFAULT}]: " output_file
output_file="${output_file//[$'\t\r\n ']}"
if [[ -z "$output_file" ]]; then
    output_file="$OUTPUT_DEFAULT"
fi

read -rp "Optional keywords (comma-separated, case-insensitive) []: " keyword_input

keywords=()
if [[ -n "$keyword_input" ]]; then
    IFS=',' read -r -a raw_keywords <<< "$keyword_input"
    for kw in "${raw_keywords[@]}"; do
        # Trim leading and trailing whitespace while preserving internal spaces.
        kw_trim="${kw#"${kw%%[![:space:]]*}"}"
        kw_trim="${kw_trim%"${kw_trim##*[![:space:]]}"}"
        if [[ -n "$kw_trim" ]]; then
            keywords+=("$kw_trim")
        fi
    done
fi

echo "Building Docker image (${IMAGE_NAME})..."
docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"

docker_args=("$start_url" "--output" "/data/$output_file")
if ((${#keywords[@]})); then
    echo "Filtering for keywords: ${keywords[*]}"
    for kw in "${keywords[@]}"; do
        docker_args+=("--require-keyword" "$kw")
    done
fi

echo "Running scraper for $start_url"
docker run --rm -v "$SCRIPT_DIR:/data" "$IMAGE_NAME" "${docker_args[@]}"

echo "Scraping complete. Combined text stored at $SCRIPT_DIR/$output_file"
