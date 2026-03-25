#!/bin/bash
# IndexNow submission script — submits all sitemap URLs to Bing/Yandex
# Usage: ./scripts/indexnow-submit.sh [--dry-run]
# Requires: curl, grep
# API: https://www.indexnow.org/documentation

set -euo pipefail

SITEMAP="deploy-static/sitemap.xml"
HOST="aeo-checker-0tao.onrender.com"
# IndexNow key — also needs to be served at /{KEY}.txt on the site
INDEXNOW_KEY="aeo-checker-indexnow-key-2026"
CACHE_FILE="scripts/.indexnow-submitted.txt"
DRY_RUN="${1:-}"

# Extract URLs from sitemap
URLS=$(grep -oP '(?<=<loc>)[^<]+' "$SITEMAP" 2>/dev/null || grep -o '<loc>[^<]*</loc>' "$SITEMAP" | sed 's/<[^>]*>//g')

if [ -z "$URLS" ]; then
  echo "ERROR: No URLs found in $SITEMAP"
  exit 1
fi

# Load cache of already-submitted URLs
touch "$CACHE_FILE"

NEW_URLS=""
TOTAL=0
SKIPPED=0

while IFS= read -r url; do
  TOTAL=$((TOTAL + 1))
  if grep -qF "$url" "$CACHE_FILE" 2>/dev/null; then
    SKIPPED=$((SKIPPED + 1))
    continue
  fi
  NEW_URLS="$NEW_URLS $url"
done <<< "$URLS"

NEW_COUNT=$(echo "$NEW_URLS" | wc -w | tr -d ' ')
echo "Sitemap: $TOTAL URLs total, $SKIPPED already submitted, $NEW_COUNT new"

if [ "$NEW_COUNT" -eq 0 ]; then
  echo "Nothing new to submit."
  exit 0
fi

if [ "$DRY_RUN" = "--dry-run" ]; then
  echo "[DRY RUN] Would submit $NEW_COUNT URLs:"
  for url in $NEW_URLS; do echo "  $url"; done
  exit 0
fi

# Build JSON payload for batch submission
URL_LIST=$(echo "$NEW_URLS" | tr ' ' '\n' | grep -v '^$' | sed 's/.*/"&"/' | paste -sd',' -)
PAYLOAD="{\"host\":\"$HOST\",\"key\":\"$INDEXNOW_KEY\",\"keyLocation\":\"https://$HOST/$INDEXNOW_KEY.txt\",\"urlList\":[$URL_LIST]}"

echo "Submitting $NEW_COUNT URLs to IndexNow..."

# Submit to Bing
BING_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "https://api.indexnow.org/IndexNow" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" 2>/dev/null || echo "000")

echo "Bing IndexNow: HTTP $BING_STATUS"

# Submit to Yandex
YANDEX_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "https://yandex.com/indexnow" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" 2>/dev/null || echo "000")

echo "Yandex IndexNow: HTTP $YANDEX_STATUS"

# Cache submitted URLs (if at least one engine accepted)
if [ "$BING_STATUS" = "200" ] || [ "$BING_STATUS" = "202" ] || [ "$YANDEX_STATUS" = "200" ] || [ "$YANDEX_STATUS" = "202" ]; then
  for url in $NEW_URLS; do
    echo "$url" >> "$CACHE_FILE"
  done
  echo "✅ $NEW_COUNT URLs cached as submitted"
else
  echo "⚠️ Neither engine accepted — URLs NOT cached (will retry next run)"
fi
