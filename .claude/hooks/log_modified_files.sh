#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"

# Extract file_path without jq dependency
# Try file_path, then path, then target_file
file_path=""
for key in file_path path target_file; do
  # Match "key": "value" pattern and extract value
  match=$(echo "$payload" | grep -oP "\"${key}\"\\s*:\\s*\"[^\"]+\"" | head -1 | sed 's/.*: *"//' | sed 's/"$//')
  if [[ -n "$match" ]]; then
    file_path="$match"
    break
  fi
done

if [[ -z "${file_path}" ]]; then
  exit 0
fi

mkdir -p .claude/_state
echo "${file_path}" >> .claude/_state/modified_files.log
exit 0
