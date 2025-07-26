"""
Field transformation utilities for mapping data between services.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FieldTransformer:
    """
    Handles field transformations and mappings between services.
    """
    
    @staticmethod
    def apply_transform(value: Any, transform: Optional[str]) -> Any:
        """
        Apply a transformation to a value.
        
        Args:
            value: The value to transform
            transform: The transformation to apply
            
        Returns:
            Transformed value
        """
        if not transform or value is None:
            return value
        
        try:
            if transform == "round":
                return round(float(value))
            elif transform == "round_to_cents":
                return round(float(value), 2)
            elif transform == "uppercase":
                return str(value).upper()
            elif transform == "lowercase":
                return str(value).lower()
            elif transform == "string":
                return str(value)
            elif transform == "int":
                return int(float(value))
            elif transform == "float":
                return float(value)
            elif transform.startswith("multiply_by_"):
                multiplier = float(transform.replace("multiply_by_", ""))
                return float(value) * multiplier
            elif transform.startswith("divide_by_"):
                divisor = float(transform.replace("divide_by_", ""))
                return float(value) / divisor
            elif transform.startswith("add_"):
                addend = float(transform.replace("add_", ""))
                return float(value) + addend
            elif transform.startswith("subtract_"):
                subtrahend = float(transform.replace("subtract_", ""))
                return float(value) - subtrahend
            else:
                logger.warning(f"Unknown transform: {transform}")
                return value
                
        except (ValueError, TypeError, ZeroDivisionError) as e:
            logger.error(f"Transform '{transform}' failed for value '{value}': {e}")
            return value
    
    @staticmethod
    def map_fields(source_data: Dict[str, Any], field_mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Map fields from source format to target format.
        
        Args:
            source_data: Data from source service
            field_mappings: List of field mapping configurations
            
        Returns:
            Mapped data in target format
        """
        target_data = {}
        
        for mapping in field_mappings:
            source_field = mapping.get("source_field")
            target_field = mapping.get("target_field")
            transform = mapping.get("transform")
            required = mapping.get("required", True)
            
            if not source_field or not target_field:
                logger.warning(f"Invalid mapping: {mapping}")
                continue
            
            # Get value from source
            source_value = source_data.get(source_field)
            
            # Check if required field is missing
            if required and source_value is None:
                logger.warning(f"Required field '{source_field}' not found in source data")
                continue
            
            # Apply transformation
            transformed_value = FieldTransformer.apply_transform(source_value, transform)
            
            # Set in target
            target_data[target_field] = transformed_value
            
        return target_data
    
    @staticmethod
    def map_item_list(source_items: List[Dict[str, Any]], field_mappings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Map a list of items from source to target format.
        
        Args:
            source_items: List of items from source service
            field_mappings: List of field mapping configurations
            
        Returns:
            List of mapped items in target format
        """
        return [
            FieldTransformer.map_fields(item, field_mappings)
            for item in source_items
        ] 