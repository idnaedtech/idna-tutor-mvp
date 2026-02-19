#!/usr/bin/env bash
set -euo pipefail

# No modified files log → allow (no edits this turn)
if [[ ! -f ".claude/_state/modified_files.log" ]]; then
  echo '{"decision":"allow"}'
  exit 0
fi

mapfile -t files < <(
  sort -u .claude/_state/modified_files.log \
  | sed '/^\s*$/d' \
  | while read -r f; do
      [[ -f "$f" ]] && echo "$f"
    done
)

# No valid files → clean up and allow
if [[ "${#files[@]}" -eq 0 ]]; then
  rm -f .claude/_state/modified_files.log
  echo '{"decision":"allow"}'
  exit 0
fi

printf "%s\n" "${files[@]}" > .claude/_state/modified_files.unique

# Files were modified → block until verify.py proof shown
cat <<'EOF'
{"decision":"block","reason":"You modified files. Run python verify.py and show ALL 14 checks passing before completing."}
EOF
