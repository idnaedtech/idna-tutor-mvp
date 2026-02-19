#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f ".claude/_state/modified_files.log" ]]; then
  exit 0
fi

mapfile -t files < <(
  sort -u .claude/_state/modified_files.log \
  | sed '/^\s*$/d' \
  | while read -r f; do
      [[ -f "$f" ]] && echo "$f"
    done
)

if [[ "${#files[@]}" -eq 0 ]]; then
  rm -f .claude/_state/modified_files.log
  exit 0
fi

printf "%s\n" "${files[@]}" > .claude/_state/modified_files.unique

# Output valid JSON without jq dependency
cat <<'EOF'
{"decision":"block","reason":"AUTO-REVIEW REQUIRED. Review ONLY files listed in .claude/_state/modified_files.unique, fix issues, then stop again."}
EOF
