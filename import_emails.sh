#!/bin/bash

# Starting year and month
year=2024
start_month=8

# Base API URL
api_url="http://discovery.rlt.sk:7667/api/import_email"

# Iterate through months from start_month to January (1)
for ((month=start_month; month>=1; month--)); do
  # Format the month to always be two digits (e.g., 01, 02, etc.)
  formatted_month=$(printf "%02d" $month)

  echo "Processing Year: $year, Month: $formatted_month..."

  # Execute the curl command
  curl_response=$(curl -s -X POST "$api_url" \
    -H "Content-Type: application/json" \
    -d "{\"year\": $year, \"month\": $month}")

  # Output the response
  echo "Response for $year-$formatted_month: $curl_response"

  # Optional: Add a sleep time if needed to avoid rate-limiting
  # sleep 1
done

echo "Finished processing all months."