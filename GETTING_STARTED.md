# Quick Start Guide

## ⚡ Get Started in 2 Minutes

1. **Install dependencies:**
   ```bash
   poetry install
   ```

2. **Test the tool (works immediately with mock API):**
   ```bash
   poetry run inventory-sync test-connection
   ```

3. **Get inventory data:**
   ```bash
   # Table format (default)
   poetry run inventory-sync get-inventory --limit 5

   # JSON format
   poetry run inventory-sync get-inventory --output json --limit 5

   # Filter by SKU
   poetry run inventory-sync get-sku-inventory "YOUR-SKU"
   ```

## 🎯 Current Status

✅ **Working Now:** ShipStation inventory retrieval  
🚧 **Next Step:** InfiPlex integration  

The tool is currently configured to use ShipStation's mock API for testing. 

## 🚀 Ready for Production?

See the [Production Setup](README.md#production-setup) section in the README for requirements:
- Gold plan or higher
- Inventory API add-on enabled  
- Production API key

## 🛠️ Available Commands

```bash
# Test connection
poetry run inventory-sync test-connection

# Get inventory (various filters)
poetry run inventory-sync get-inventory [OPTIONS]
  --sku TEXT              Filter by SKU
  --warehouse-id TEXT     Filter by warehouse
  --location-id TEXT      Filter by location  
  --group-by [warehouse|location]  Group results
  --limit INTEGER         Limit results
  --all-pages            Fetch all pages
  --output [table|json]  Output format

# Get specific SKU
poetry run inventory-sync get-sku-inventory SKU
``` 