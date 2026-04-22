#!/usr/bin/env bash
# Validate all kavachiq.com URLs referenced in docs/sales/*.md.
# Usage: scripts/check-sales-links.sh
# Exits non-zero if any URL returns a non-2xx final status.

set -uo pipefail

DOCS_DIR="docs/sales"
URL_PATTERN='https://kavachiq\.com[a-zA-Z0-9/_.?#=&-]+'
LEGACY_PATHS="/demo"

# Extract unique URLs referenced in docs/sales/*.md (portable, no mapfile)
URL_LIST=$(grep -rhoE "$URL_PATTERN" "$DOCS_DIR"/*.md | sed 's/[.,)>]*$//' | sort -u)

if [ -z "$URL_LIST" ]; then
  echo "No kavachiq.com URLs found under $DOCS_DIR/"
  exit 0
fi

count=$(echo "$URL_LIST" | wc -l | tr -d ' ')
echo "Validating $count unique URL(s) from $DOCS_DIR/"
echo

failures=0
while IFS= read -r url; do
  [ -z "$url" ] && continue
  result=$(curl -s -o /dev/null -w "%{http_code} %{num_redirects} -> %{url_effective}" -L --max-time 10 "$url")
  code="${result%% *}"
  case "$code" in
    2*) printf "  ok   %s  [%s]\n" "$url" "$result" ;;
    *)  printf "  FAIL %s  [%s]\n" "$url" "$result"
        failures=$((failures + 1)) ;;
  esac
done <<EOF
$URL_LIST
EOF

echo
echo "Checking that no legacy paths are referenced:"
legacy_hits=0
for path in $LEGACY_PATHS; do
  hits=$(grep -rEn "kavachiq\.com${path}([/\"' )]|$)" "$DOCS_DIR"/*.md || true)
  if [ -n "$hits" ]; then
    echo "  FAIL legacy path $path referenced:"
    echo "$hits" | sed 's/^/    /'
    legacy_hits=$((legacy_hits + 1))
  else
    echo "  ok   no references to $path"
  fi
done

echo
if [ "$failures" -gt 0 ] || [ "$legacy_hits" -gt 0 ]; then
  echo "Result: $failures URL failure(s), $legacy_hits legacy-path reference(s)."
  exit 1
fi
echo "Result: all clean."
