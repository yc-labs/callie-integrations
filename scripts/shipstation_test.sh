#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   export SS_KEY="<your-shipstation-api-key>"
#   bash shipstation_inventory_count.sh
# Optional filters you can append to BASE (examples shown commented):
#   sku=SKU1,SKU2
#   inventory_warehouse_id=...
#   inventory_location_id=...
#   group_by=warehouse   # or: location
#   limit=1000           # page size; ShipStation returns a `links.next` cursor

if [[ -z "${SS_KEY:-}" ]]; then
  echo "SS_KEY env var is not set. Export your ShipStation API key first." >&2
  echo "Example: export SS_KEY='3Ml097q21mPW5HjZJSIHl8zwyHCm63HFVQDwTZNKSP4'" >&2
  exit 1
fi

BASE="https://api.shipstation.com/v2/inventory?limit=1000"

url="$BASE"
seen=()
total=0
page=0

while [[ -n "$url" ]]; do
  json=$(curl -sS -H "api-key: $SS_KEY" "$url")

  # Count items on this page
  count=$(jq '.inventory | length' <<<"$json")
  total=$(( total + count ))
  page=$(( page + 1 ))
  echo "page=$page  fetched=$count  running_total=$total"

  # Resolve next link: can be a string URL or an object with `href`
  next=$(jq -r '(.links.next // empty) | (if type=="object" then .href else . end // "")' <<<"$json")

  # Stop if no next, or next repeats, or next equals current (some APIs do this at the end)
  if [[ -z "$next" || "$next" == "$url" ]]; then
    break
  fi
  for s in "${seen[@]}"; do
    if [[ "$s" == "$next" ]]; then
      next=""
      break
    fi
  done
  if [[ -z "$next" ]]; then
    break
  fi

  seen+=("$url")
  url="$next"
  # Safety: hard cap on iterations
  if [[ ${#seen[@]} -ge 10000 ]]; then
    echo "Hit safety cap at 10,000 pages; stopping." >&2
    break
  fi

done

echo "TOTAL_RECORDS=$total"
