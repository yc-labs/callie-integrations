"""
AI-powered transformation mapper using Google Gemini to intelligently suggest field mappings
between different connectors based on their schemas.
"""
import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from google import genai
from google.genai import types
from google.cloud import secretmanager

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.callie.connectors import CONNECTOR_REGISTRY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AITransformationMapper:
    """AI-powered mapper that suggests field transformations between connectors."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI mapper with Gemini API."""
        if not api_key:
            # Try to get API key from Google Secret Manager
            api_key = self._get_api_key_from_secret_manager()
        
        if not api_key:
            raise ValueError("Gemini API key not provided and not found in Secret Manager")
        
        # Create client with API key
        self.client = genai.Client(api_key=api_key)
        self.model_name = 'gemini-2.0-flash-001'
        
    def _get_api_key_from_secret_manager(self) -> Optional[str]:
        """Retrieve Gemini API key from Google Secret Manager."""
        try:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "yc-partners")
            client = secretmanager.SecretManagerServiceClient()
            
            # Try common secret names
            secret_names = ["gemini-api-key", "GEMINI_API_KEY", "GOOGLE_AI_API_KEY", "GENAI_API_KEY"]
            
            for secret_name in secret_names:
                try:
                    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                    response = client.access_secret_version(request={"name": name})
                    return response.payload.data.decode("UTF-8")
                except Exception:
                    continue
                    
            logger.warning("Could not find Gemini API key in Secret Manager")
            return None
            
        except Exception as e:
            logger.error(f"Error accessing Secret Manager: {e}")
            return None
    
    def get_sample_data(self, connector_type: str, operation: str = "read") -> Dict[str, Any]:
        """Get sample data from a connector to help with mapping."""
        # This is a placeholder - in a real implementation, we'd actually
        # call the connector with test credentials to get real sample data
        
        if connector_type == "feedonomics" and operation == "read_orders":
            return {
                "id": "12345",
                "marketplace_order_number": "ORD-2024-001",
                "marketplace_name": "Target Plus",
                "customer": {
                    "full_name": "John Doe",
                    "email": "john@example.com",
                    "phone": "555-1234"
                },
                "shipping_address": {
                    "address1": "123 Main St",
                    "city": "Anytown",
                    "state": "CA",
                    "postal_code": "12345"
                },
                "line_items": [
                    {
                        "sku": "PROD-001",
                        "quantity": 2,
                        "unit_price": 29.99
                    }
                ]
            }
        elif connector_type == "infiplex" and operation == "create_order":
            return {
                "order_id": "required_string",
                "customer_name": "required_string",
                "customer_email": "optional_string",
                "delivery_address": {
                    "street": "required_string",
                    "city": "required_string",
                    "state": "required_string",
                    "zip": "required_string"
                },
                "items": [
                    {
                        "sku": "required_string",
                        "qty": "required_integer",
                        "price": "required_float"
                    }
                ]
            }
        
        return {}
    
    def suggest_mappings(
        self,
        source_connector: str,
        target_connector: str,
        source_operation: str = "read",
        target_operation: str = "write",
        include_sample_data: bool = True
    ) -> List[Dict[str, Any]]:
        """Use AI to suggest field mappings between two connectors."""
        
        # Get connector schemas
        source_class = CONNECTOR_REGISTRY.get(source_connector)
        target_class = CONNECTOR_REGISTRY.get(target_connector)
        
        if not source_class or not target_class:
            raise ValueError(f"Invalid connector types: {source_connector} or {target_connector}")
        
        # Create dummy instances to get schemas
        dummy_creds = {"api_key": "dummy"}
        source_instance = source_class(credentials=dummy_creds, base_url="http://dummy")
        target_instance = target_class(credentials=dummy_creds, base_url="http://dummy")
        
        # Get schemas based on operation type
        source_schema = None
        target_schema = None
        
        if "order" in source_operation.lower():
            source_schema = source_instance.get_orders_schema()
        elif "inventory" in source_operation.lower():
            source_schema = source_instance.get_inventory_schema()
            
        if "order" in target_operation.lower():
            target_schema = target_instance.get_orders_schema()
        elif "inventory" in target_operation.lower():
            target_schema = target_instance.get_inventory_schema()
        
        # Get sample data if requested
        source_sample = self.get_sample_data(source_connector, source_operation) if include_sample_data else {}
        target_sample = self.get_sample_data(target_connector, target_operation) if include_sample_data else {}
        
        # Prepare prompt for Gemini
        prompt = self._create_mapping_prompt(
            source_connector, target_connector,
            source_schema, target_schema,
            source_sample, target_sample
        )
        
        # Get AI suggestions
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            mappings = self._parse_ai_response(response.text)
            return mappings
        except Exception as e:
            logger.error(f"Error getting AI suggestions: {e}")
            return []
    
    def _create_mapping_prompt(
        self,
        source_connector: str,
        target_connector: str,
        source_schema: Any,
        target_schema: Any,
        source_sample: Dict,
        target_sample: Dict
    ) -> str:
        """Create a detailed prompt for the AI model."""
        
        prompt = f"""You are an expert data integration specialist. Your task is to suggest field mappings between two systems.

SOURCE SYSTEM: {source_connector}
TARGET SYSTEM: {target_connector}

SOURCE SCHEMA:
{json.dumps(source_schema.model_dump() if source_schema else {}, indent=2)}

TARGET SCHEMA:
{json.dumps(target_schema.model_dump() if target_schema else {}, indent=2)}

SOURCE SAMPLE DATA:
{json.dumps(source_sample, indent=2)}

TARGET EXPECTED FORMAT:
{json.dumps(target_sample, indent=2)}

Please analyze the schemas and sample data to suggest field mappings. Consider:
1. Field names and their semantic meaning
2. Data types and required transformations
3. Nested structures that need to be flattened or restructured
4. Fields that might need to be combined or split

Output your response as a JSON array of mapping objects, where each object has:
- source_field: The path to the source field (use dot notation for nested fields)
- target_field: The path to the target field
- transformation: Optional transformation needed (e.g., "concatenate", "split", "convert_date", etc.)
- notes: Brief explanation of the mapping

Example format:
[
  {{
    "source_field": "customer.full_name",
    "target_field": "customer_name",
    "transformation": null,
    "notes": "Direct mapping of customer name"
  }},
  {{
    "source_field": "shipping_address.postal_code",
    "target_field": "delivery_address.zip",
    "transformation": null,
    "notes": "Postal code to zip code mapping"
  }}
]

IMPORTANT: Only output the JSON array, no additional text or explanation."""
        
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse the AI response into field mapping dictionaries."""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                mappings_data = json.loads(json_str)
            else:
                # Try parsing the entire response as JSON
                mappings_data = json.loads(response_text)
            
            # Return as dictionaries
            field_mappings = []
            for mapping in mappings_data:
                field_mappings.append({
                    'source_field': mapping["source_field"],
                    'target_field': mapping["target_field"],
                    'transformation': mapping.get('transformation'),
                    'notes': mapping.get('notes', '')
                })
            
            return field_mappings
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            logger.debug(f"Response text: {response_text}")
            return []
    
    def interactive_mapping(
        self,
        source_connector: str,
        target_connector: str,
        source_operation: str = "read_orders",
        target_operation: str = "create_order"
    ) -> Dict[str, Any]:
        """Interactive CLI tool for creating and refining mappings."""
        
        print(f"\n🤖 AI Transformation Mapper")
        print(f"{'='*50}")
        print(f"Source: {source_connector} ({source_operation})")
        print(f"Target: {target_connector} ({target_operation})")
        print(f"{'='*50}\n")
        
        # Get AI suggestions
        print("🔍 Analyzing schemas and generating mapping suggestions...")
        mappings = self.suggest_mappings(
            source_connector, target_connector,
            source_operation, target_operation
        )
        
        if not mappings:
            print("❌ No mappings could be generated automatically.")
            return {"mappings": []}
        
        print(f"\n✅ Generated {len(mappings)} mapping suggestions:\n")
        
        # Display and allow editing
        final_mappings = []
        for i, mapping in enumerate(mappings, 1):
            print(f"{i}. {mapping['source_field']} → {mapping['target_field']}")
            
            # Allow user to accept, modify, or reject
            action = input("   [A]ccept, [M]odify, [S]kip? (default: A): ").strip().upper() or 'A'
            
            if action == 'A':
                final_mappings.append(mapping)
                print("   ✓ Accepted")
            elif action == 'M':
                new_source = input(f"   New source field (current: {mapping['source_field']}): ").strip() or mapping['source_field']
                new_target = input(f"   New target field (current: {mapping['target_field']}): ").strip() or mapping['target_field']
                final_mappings.append({
                    'source_field': new_source,
                    'target_field': new_target
                })
                print("   ✓ Modified")
            else:
                print("   ✗ Skipped")
            
            print()
        
        # Allow adding custom mappings
        print("\nWould you like to add any custom mappings?")
        while True:
            add_more = input("[Y]es or [N]o (default: N): ").strip().upper() or 'N'
            if add_more != 'Y':
                break
                
            source_field = input("Source field: ").strip()
            target_field = input("Target field: ").strip()
            if source_field and target_field:
                final_mappings.append({
                    'source_field': source_field,
                    'target_field': target_field
                })
                print("✓ Added custom mapping")
            print()
        
        # Generate configuration
        config = {
            "mappings": [m.model_dump() for m in final_mappings]
        }
        
        print(f"\n{'='*50}")
        print("📋 Final Transformation Configuration:")
        print(json.dumps(config, indent=2))
        print(f"{'='*50}\n")
        
        # Save to file
        save = input("Save to file? [Y]es or [N]o (default: Y): ").strip().upper() or 'Y'
        if save == 'Y':
            filename = f"mappings_{source_connector}_to_{target_connector}.json"
            with open(filename, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"✅ Saved to {filename}")
        
        return config


def main():
    """Main entry point for the AI transformation mapper."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI-powered transformation mapper for Callie Integrations")
    parser.add_argument("source", help="Source connector (e.g., feedonomics)")
    parser.add_argument("target", help="Target connector (e.g., infiplex)")
    parser.add_argument("--source-op", default="read_orders", help="Source operation")
    parser.add_argument("--target-op", default="create_order", help="Target operation")
    parser.add_argument("--api-key", help="Gemini API key (if not using Secret Manager)")
    parser.add_argument("--non-interactive", action="store_true", help="Just show suggestions without interaction")
    
    args = parser.parse_args()
    
    try:
        mapper = AITransformationMapper(api_key=args.api_key)
        
        if args.non_interactive:
            mappings = mapper.suggest_mappings(
                args.source, args.target,
                args.source_op, args.target_op
            )
            config = {"mappings": [m.model_dump() for m in mappings]}
            print(json.dumps(config, indent=2))
        else:
            mapper.interactive_mapping(
                args.source, args.target,
                args.source_op, args.target_op
            )
            
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()