#!/bin/bash
# IndexNow submission script for AEO Checker
# Submits all sitemap URLs to Bing/Yandex via IndexNow API
# Usage: ./indexnow-submit.sh [--all | --new-only]
#
# IndexNow API: https://www.indexnow.org/documentation
# No API key rotation needed — key is self-hosted at /indexnow-key.txt

SITE_URL="https://aeo-checker-0tao.onrender.com"
KEY="aeo-checker-indexnow-key-2026"
KEY_LOCATION="${SITE_URL}/${KEY}.txt"
CACHE_FILE="$(dirname "$0")/.indexnow-submitted.txt"
SITEMAP_URL="${SITE_URL}/sitemap.xml"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "📡 IndexNow Submission — $(date '+%Y-%m-%d %H:%M')"
echo "   Site: ${SITE_URL}"
echo ""

# Fetch sitemap and extract URLs
URLS=$(curl -s "$SITEMAP_URL" | grep -o '<loc>[^<]*</loc>' | sed 's/<loc>//g;s/<\/loc>//g')
TOTAL=$(echo "$URLS" | wc -l | tr -d ' ')

echo "📄 Found ${TOTAL} URLs in sitemap"

# Filter to new-only if requested
if [[ "$1" == "--new-only" ]] && [[ -f "$CACHE_FILE" ]]; then
    NEW_URLS=""
    while IFS= read -r url; do
        if ! grep -qF "$url" "$CACHE_FILE" 2>/dev/null; then
            NEW_URLS="${NEW_URLS}${url}\n"
        fi
    done <<< "$URLS"
    URLS=$(echo -e "$NEW_URLS" | sed '/^$/d')
    NEW_COUNT=$(echo "$URLS" | sed '/^$/d' | wc -l | tr -d ' ')
    echo "🆕 ${NEW_COUNT} new URLs (not previously submitted)"
    if [[ "$NEW_COUNT" -eq 0 ]]; then
        echo -e "${GREEN}✅ All URLs already submitted. Nothing to do.${NC}"
        exit 0
    fi
else
    echo "📤 Submitting all ${TOTAL} URLs"
fi

# Build URL list JSON array
URL_LIST=""
while IFS= read -r url; do
    [[ -z "$url" ]] && continue
    if [[ -n "$URL_LIST" ]]; then
        URL_LIST="${URL_LIST},"
    fi
    URL_LIST="${URL_LIST}\"${url}\""
done <<< "$URLS"

# Submit to IndexNow (Bing endpoint — also notifies Yandex, Seznam, Naver)
PAYLOAD="{\"host\":\"aeo-checker-0tao.onrender.com\",\"key\":\"${KEY}\",\"keyLocation\":\"${KEY_LOCATION}\",\"urlList\":[${URL_LIST}]}"

echo ""
echo "🔄 Submitting to IndexNow (api.indexnow.org)..."

RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "https://api.indexnow.org/indexnow" \
    -H "Content-Type: application/json; charset=utf-8" \
    -d "$PAYLOAD")

if [[ "$RESPONSE" == "200" ]] || [[ "$RESPONSE" == "202" ]]; then
    echo -e "${GREEN}✅ Success! HTTP ${RESPONSE} — URLs accepted${NC}"
    # Update cache
    echo "$URLS" >> "$CACHE_FILE"
    sort -u "$CACHE_FILE" -o "$CACHE_FILE" 2>/dev/null
    echo "   Cache updated: ${CACHE_FILE}"
elif [[ "$RESPONSE" == "422" ]]; then
    echo -e "${YELLOW}⚠️ HTTP 422 — Key not found at ${KEY_LOCATION}${NC}"
    echo "   Need to create ${KEY}.txt at site root"
elif [[ "$RESPONSE" == "429" ]]; then
    echo -e "${YELLOW}⚠️ HTTP 429 — Rate limited. Try again later.${NC}"
else
    echo -e "${RED}❌ HTTP ${RESPONSE} — Submission failed${NC}"
fi

echo ""
echo "Done. URLs submitted: $(echo "$URLS" | sed '/^$/d' | wc -l | tr -d ' ')"
