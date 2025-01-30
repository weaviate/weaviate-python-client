from typing import List

from .models import AppendPropertyOperation, DataType, UpdatePropertyOperation


class Operations:
    """Factory class for creating transformation operations."""

    @staticmethod
    def append_property(
        property_name: str,
        data_type: DataType,
        view_properties: List[str],
        instruction: str,
    ) -> AppendPropertyOperation:
        """Create an operation to append a new property.

        Args:
            property_name: Name of the new property to append
            data_type: Data type of the new property
            view_properties: List of property names to use as context for the transformation
            instruction: Instruction for how to generate the new property value

        Returns:
            An AppendPropertyOperation object
        """
        return AppendPropertyOperation(
            property_name=property_name,
            data_type=data_type,
            view_properties=view_properties,
            instruction=instruction,
        )

    @staticmethod
    def update_property(
        property_name: str,
        view_properties: List[str],
        instruction: str,
    ) -> UpdatePropertyOperation:
        """Create an operation to update an existing property.

        Args:
            property_name: Name of the property to update
            view_properties: List of property names to use as context for the transformation
            instruction: Instruction for how to update the property value

        Returns:
            An UpdatePropertyOperation object
        """
        return UpdatePropertyOperation(
            property_name=property_name,
            view_properties=view_properties,
            instruction=instruction,
        )