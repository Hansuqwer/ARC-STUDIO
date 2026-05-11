#!/usr/bin/env bash
set -euo pipefail

missing=0
while IFS= read -r package_json; do
  if ! node -e "const fs=require('fs'); const p=JSON.parse(fs.readFileSync(process.argv[1], 'utf8')); process.exit(p.private || p.license ? 0 : 1)" "$package_json"; then
    echo "Missing license: $package_json" >&2
    missing=1
  fi
done < <(git ls-files '*package.json' ':!:**/node_modules/**' ':!:**/src-gen/**')

if [ "$missing" -ne 0 ]; then
  exit 1
fi

echo "License check passed. Workspace packages declare licenses or are private."
