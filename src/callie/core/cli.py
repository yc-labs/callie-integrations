"""Command line interface for inventory sync."""

import sys
import json
import logging
from typing import Optional

import click
from dotenv import load_dotenv

from .config import setup_logging, load_environment
from ..integrations.shipstation.client import create_client_from_env, ShipStationAPIError
from ..integrations.infiplex.client import create_infiplex_client_from_env, InfiPlexAPIError
from .models import InventoryFilter


@click.group()
@click.option('--log-level', default='INFO', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Set the logging level')
@click.option('--env-file', type=click.Path(exists=True), help='Path to .env file')
def cli(log_level: str, env_file: Optional[str]) -> None:
    """ShipStation to InfiPlex Inventory Sync Tool."""
    setup_logging(log_level)
    load_environment(env_file)


@cli.command()
@click.option('--sku', help='Filter by specific SKU')
@click.option('--warehouse-id', help='Filter by warehouse ID')
@click.option('--location-id', help='Filter by location ID')
@click.option('--group-by', type=click.Choice(['warehouse', 'location']), 
              help='Group results by warehouse or location')
@click.option('--limit', type=int, help='Limit number of results')
@click.option('--all-pages', is_flag=True, help='Fetch all pages of results')
@click.option('--output', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
def get_inventory(sku: Optional[str], warehouse_id: Optional[str], location_id: Optional[str],
                 group_by: Optional[str], limit: Optional[int], all_pages: bool, 
                 output: str) -> None:
    """Get inventory levels from ShipStation."""
    try:
        # Create client
        client = create_client_from_env()
        
        # Create filters
        filters = InventoryFilter(
            sku=sku,
            inventory_warehouse_id=warehouse_id,
            inventory_location_id=location_id,
            group_by=group_by,
            limit=limit
        )
        
        # Fetch inventory
        if all_pages:
            click.echo("Fetching all inventory pages...")
            inventory_items = client.get_all_inventory(filters)
            
            if output == 'json':
                # Convert to dict for JSON output
                items_data = [item.model_dump() for item in inventory_items]
                click.echo(json.dumps({
                    'inventory': items_data,
                    'total': len(inventory_items)
                }, indent=2))
            else:
                _display_inventory_table(inventory_items)
                click.echo(f"\nTotal items: {len(inventory_items)}")
        else:
            click.echo("Fetching inventory...")
            response = client.get_inventory(filters)
            
            if output == 'json':
                click.echo(response.model_dump_json(indent=2))
            else:
                _display_inventory_table(response.inventory)
                click.echo(f"\nPage {response.page} of {response.pages} (Total: {response.total})")
        
    except ShipStationAPIError as e:
        click.echo(f"ShipStation API Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Configuration Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logging.exception("Unexpected error occurred")
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('sku')
def get_sku_inventory(sku: str) -> None:
    """Get inventory for a specific SKU."""
    try:
        client = create_client_from_env()
        inventory_items = client.get_inventory_by_sku(sku)
        
        if not inventory_items:
            click.echo(f"No inventory found for SKU: {sku}")
            return
        
        _display_inventory_table(inventory_items)
        
    except ShipStationAPIError as e:
        click.echo(f"ShipStation API Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Configuration Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logging.exception("Unexpected error occurred")
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


def _display_inventory_table(inventory_items) -> None:
    """Display inventory items in a table format."""
    if not inventory_items:
        click.echo("No inventory items found.")
        return
    
    # Header
    click.echo(f"{'SKU':<20} {'On Hand':<10} {'Allocated':<10} {'Available':<10} {'Avg Cost':<12} {'Warehouse':<15} {'Location':<15}")
    click.echo("-" * 100)
    
    # Rows
    for item in inventory_items:
        cost_str = f"{item.average_cost.amount:.2f} {item.average_cost.currency}"
        allocated_str = str(item.allocated) if item.allocated is not None else "N/A"
        warehouse_str = item.inventory_warehouse_id or "N/A"
        location_str = item.inventory_location_id or "N/A"
        click.echo(f"{item.sku:<20} {item.on_hand:<10} {allocated_str:<10} {item.available:<10} "
                  f"{cost_str:<12} {warehouse_str:<15} {location_str:<15}")


@cli.command()
def test_connection() -> None:
    """Test connection to ShipStation API."""
    try:
        client = create_client_from_env()
        
        # Try to fetch a small amount of inventory to test the connection
        filters = InventoryFilter(limit=1)
        response = client.get_inventory(filters)
        
        click.echo("✅ Successfully connected to ShipStation API!")
        click.echo(f"Total inventory items available: {response.total}")
        
    except ShipStationAPIError as e:
        click.echo(f"❌ ShipStation API Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"❌ Configuration Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logging.exception("Unexpected error occurred")
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
def test_infiplex() -> None:
    """Test connection to InfiPlex API."""
    try:
        client = create_infiplex_client_from_env()
        result = client.test_connection()
        
        if result["status"] == "success":
            click.echo("✅ Successfully connected to InfiPlex API!")
            click.echo(f"Message: {result['message']}")
            if 'sample_data' in result and result['sample_data']:
                click.echo("Sample inventory data available.")
        else:
            click.echo(f"❌ InfiPlex API Error: {result['message']}", err=True)
            sys.exit(1)
        
    except ValueError as e:
        click.echo(f"❌ Configuration Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logging.exception("Unexpected error occurred")
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('sku')
@click.option('--warehouse-id', type=int, help='Warehouse ID to check specific warehouse inventory')
def get_infiplex_inventory(sku: str, warehouse_id: Optional[int]) -> None:
    """Get inventory quantity for a SKU from InfiPlex."""
    try:
        client = create_infiplex_client_from_env()
        quantity = client.get_inventory_info(sku, warehouse_id)
        
        if quantity is not None:
            warehouse_info = f" (Warehouse {warehouse_id})" if warehouse_id else " (Total)"
            click.echo(f"SKU: {sku}")
            click.echo(f"Quantity{warehouse_info}: {quantity}")
        else:
            click.echo(f"No inventory found for SKU: {sku}")
        
    except InfiPlexAPIError as e:
        click.echo(f"InfiPlex API Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Configuration Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logging.exception("Unexpected error occurred")
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('sku')
@click.argument('quantity', type=int)
@click.option('--warehouse-id', type=int, help='Warehouse ID to update specific warehouse inventory')
def update_infiplex_inventory(sku: str, quantity: int, warehouse_id: Optional[int]) -> None:
    """Update inventory quantity for a SKU in InfiPlex."""
    try:
        client = create_infiplex_client_from_env()
        
        # Get current quantity first
        current_qty = client.get_inventory_info(sku, warehouse_id)
        if current_qty:
            click.echo(f"Current quantity: {current_qty}")
        
        success = client.update_inventory(sku, quantity, warehouse_id)
        
        if success:
            warehouse_info = f" in warehouse {warehouse_id}" if warehouse_id else ""
            click.echo(f"✅ Successfully updated SKU {sku}{warehouse_info} to quantity {quantity}")
        else:
            click.echo(f"❌ Failed to update inventory for SKU: {sku}")
            sys.exit(1)
        
    except InfiPlexAPIError as e:
        click.echo(f"InfiPlex API Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Configuration Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logging.exception("Unexpected error occurred")
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('sku')
@click.option('--warehouse-id', type=int, help='Warehouse ID to sync to specific warehouse')
def sync_sku(sku: str, warehouse_id: Optional[int]) -> None:
    """Sync a single SKU from ShipStation to InfiPlex."""
    try:
        # Get data from ShipStation
        ss_client = create_client_from_env()
        ss_inventory = ss_client.get_inventory_by_sku(sku)
        
        if not ss_inventory:
            click.echo(f"❌ SKU {sku} not found in ShipStation")
            sys.exit(1)
        
        # Get InfiPlex client
        ip_client = create_infiplex_client_from_env()
        
        # Show current states
        click.echo("📊 Current Inventory Status:")
        for item in ss_inventory:
            click.echo(f"ShipStation - SKU: {item.sku}, Available: {item.available}")
            
            # Get current InfiPlex quantity
            current_ip_qty = ip_client.get_inventory_info(sku, warehouse_id)
            warehouse_info = f" (Warehouse {warehouse_id})" if warehouse_id else ""
            click.echo(f"InfiPlex{warehouse_info} - SKU: {sku}, Current: {current_ip_qty or 'Not Found'}")
            
            # Update InfiPlex with ShipStation quantity
            click.echo(f"\n🔄 Syncing {item.available} units to InfiPlex...")
            success = ip_client.update_inventory(sku, item.available, warehouse_id)
            
            if success:
                click.echo(f"✅ Successfully synced SKU {sku}")
            else:
                click.echo(f"❌ Failed to sync SKU {sku}")
                sys.exit(1)
        
    except (ShipStationAPIError, InfiPlexAPIError) as e:
        click.echo(f"API Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Configuration Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logging.exception("Unexpected error occurred")
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--warehouse-id', type=int, help='Warehouse ID to sync to specific warehouse')
@click.option('--limit', type=int, default=10, help='Number of SKUs to sync (default: 10)')
@click.option('--all-skus', is_flag=True, help='Sync all SKUs (overrides limit)')
@click.option('--dry-run', is_flag=True, help='Show what would be synced without making changes')
@click.option('--validate-only', is_flag=True, help='Only validate - show sync status without making changes')
def bulk_sync(warehouse_id: Optional[int], limit: int, all_skus: bool, dry_run: bool, validate_only: bool) -> None:
    """Sync multiple SKUs from ShipStation to InfiPlex."""
    try:
        # Get data from ShipStation
        ss_client = create_client_from_env()
        
        if all_skus:
            click.echo("🔄 Fetching ALL SKUs from ShipStation...")
            inventory_items = ss_client.get_all_inventory()
        else:
            click.echo(f"🔄 Fetching {limit} SKUs from ShipStation...")
            filters = InventoryFilter(limit=limit)
            response = ss_client.get_inventory(filters)
            inventory_items = response.inventory
        
        if not inventory_items:
            click.echo("❌ No inventory found in ShipStation")
            sys.exit(1)
        
        # Get InfiPlex client
        ip_client = create_infiplex_client_from_env()
        
        successful_syncs = 0
        failed_syncs = 0
        matching_items = 0
        mismatched_items = 0
        not_found_items = 0
        sync_data = []
        
        click.echo(f"\n📊 Found {len(inventory_items)} SKUs to process:")
        click.echo("-" * 100)
        
        for item in inventory_items:
            sku = item.sku
            available = item.available
            
            # Get current InfiPlex quantity for comparison
            current_qty = ip_client.get_inventory_info(sku, warehouse_id)
            current_display = current_qty if current_qty and current_qty.isdigit() else "Not Found"
            
            # Determine status
            if current_qty and current_qty.isdigit():
                current_int = int(current_qty)
                if current_int == available:
                    status = "✅ MATCH"
                    matching_items += 1
                else:
                    status = "⚠️ DIFF"
                    mismatched_items += 1
            else:
                status = "❓ NOT_FOUND"
                not_found_items += 1
            
            click.echo(f"SKU: {sku:<20} | SS: {available:<5} | IP: {current_display:<10} | {status:<12}", nl=False)
            
            if dry_run or validate_only:
                if validate_only:
                    click.echo("")
                else:
                    click.echo(" | DRY RUN")
                continue
            
            # Only sync if there's a difference or item not found
            if status != "✅ MATCH":
                success = ip_client.update_inventory(sku, available, warehouse_id)
                
                if success:
                    successful_syncs += 1
                    click.echo(" | ✅ SYNCED")
                    sync_data.append({
                        'sku': sku, 
                        'quantity_to_set': available, 
                        'warehouse_id': warehouse_id
                    })
                else:
                    failed_syncs += 1
                    click.echo(" | ❌ FAILED")
            else:
                click.echo(" | ⏭️ SKIP")
        
        if dry_run:
            click.echo(f"\n🔍 DRY RUN COMPLETE: Would sync {len(response.inventory)} SKUs")
            return
        
        # Summary
        click.echo("-" * 80)
        click.echo(f"📈 Sync Summary:")
        click.echo(f"  ✅ Successful: {successful_syncs}")
        click.echo(f"  ❌ Failed: {failed_syncs}")
        click.echo(f"  📦 Total: {len(response.inventory)}")
        
        if warehouse_id:
            click.echo(f"  🏭 Warehouse: {warehouse_id}")
        else:
            click.echo(f"  🏭 Warehouse: Total inventory")
        
    except (ShipStationAPIError, InfiPlexAPIError) as e:
        click.echo(f"API Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Configuration Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logging.exception("Unexpected error occurred")
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    cli() 