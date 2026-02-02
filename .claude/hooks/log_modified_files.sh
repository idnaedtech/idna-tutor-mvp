#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"

file_path="$(
  jq -r '
    .tool_input.file_path
    // .tool_input.path
    // .tool_input.target_file
    // empty
  ' <<<"$payload"
)"

if [[ -z "${file_path}" ]]; then
  exit 0
fi

mkdir -p .claude/_state
echo "${file_path}" >> .claude/_state/modified_files.log
exit 0
