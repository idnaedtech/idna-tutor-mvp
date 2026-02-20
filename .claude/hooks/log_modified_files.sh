#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"

# Extract file_path without jq dependency (Windows-compatible, no grep -P)
# Try file_path, then path, then target_file
file_path=""
for key in file_path path target_file; do
  # Use sed to extract value - works on Windows Git Bash
  match=$(echo "$payload" | sed -n "s/.*\"${key}\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" | head -1)
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
