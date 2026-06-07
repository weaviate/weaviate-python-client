from typing import Sequence, Union

import pytest

from weaviate.collections.classes.tenants import Tenant, TenantCreate, TenantUpdate
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.validator import _validate_input, _ValidateArgument


def test_tenant_create_sequence_validation_rejects_mixed_invalid_values() -> None:
    with pytest.raises(WeaviateInvalidInputError):
        _validate_input(
            _ValidateArgument(
                expected=[Tenant, TenantCreate, Sequence[Union[str, Tenant, TenantCreate]]],
                name="tenants",
                value=[Tenant(name="tenant-a"), object()],
            )
        )


def test_tenant_update_sequence_validation_rejects_mixed_invalid_values() -> None:
    with pytest.raises(WeaviateInvalidInputError):
        _validate_input(
            _ValidateArgument(
                expected=[Tenant, TenantUpdate, Sequence[Union[Tenant, TenantUpdate]]],
                name="tenants",
                value=[Tenant(name="tenant-a"), object()],
            )
        )


def test_tenant_sequence_validation_accepts_valid_values() -> None:
    _validate_input(
        _ValidateArgument(
            expected=[Tenant, TenantCreate, Sequence[Union[str, Tenant, TenantCreate]]],
            name="tenants",
            value=["tenant-a", Tenant(name="tenant-b"), TenantCreate(name="tenant-c")],
        )
    )

    _validate_input(
        _ValidateArgument(
            expected=[Tenant, TenantUpdate, Sequence[Union[Tenant, TenantUpdate]]],
            name="tenants",
            value=[Tenant(name="tenant-a"), TenantUpdate(name="tenant-b")],
        )
    )
