#!/bin/bash

set -e

# Configuration
WAREHOUSE_ID=${WAREHOUSE_ID:-17}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔍 Validating inventory sync status${NC}"
echo "Warehouse ID: $WAREHOUSE_ID"
echo

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ pyproject.toml not found. Please run from project root.${NC}"
    exit 1
fi

# Run validation
echo -e "${YELLOW}📊 Running validation check...${NC}"
poetry run inventory-sync bulk-sync --all-skus --warehouse-id $WAREHOUSE_ID --validate-only

echo
echo -e "${GREEN}✅ Validation completed!${NC}" 