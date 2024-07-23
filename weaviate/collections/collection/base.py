from typing import Any, Generic, Optional, Type, cast
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.internal import (
    References,
)
from weaviate.collections.classes.tenants import Tenant
from weaviate.collections.classes.types import Properties
from weaviate.collections.config import _ConfigCollectionAsync
from weaviate.collections.query import _QueryCollectionAsync
from weaviate.connect import ConnectionV4
from weaviate.util import _capitalize_first_letter
from weaviate.validator import _validate_input, _ValidateArgument


def _with_tenant(cls: Any, **kwargs) -> Any:
    if kwargs["validate_arguments"]:
        _validate_input(
            [_ValidateArgument(expected=[str, Tenant, None], name="tenant", value=kwargs["tenant"])]
        )
    return cls(**kwargs)


def _with_consistency_level(cls: Any, **kwargs) -> Any:
    if kwargs["validate_arguments"]:
        _validate_input(
            [
                _ValidateArgument(
                    expected=[ConsistencyLevel, None],
                    name="consistency_level",
                    value=kwargs["consistency_level"],
                )
            ]
        )
    return cls(**kwargs)


class _CollectionBase(Generic[Properties, References]):
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        validate_arguments: bool,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
        properties: Optional[Type[Properties]] = None,
        references: Optional[Type[References]] = None,
    ) -> None:
        self._connection = connection
        self.name = _capitalize_first_letter(name)
        self._validate_arguments = validate_arguments

        self._config = _ConfigCollectionAsync(connection, name, tenant)
        self._query = _QueryCollectionAsync[Properties, References](
            connection,
            name,
            consistency_level,
            tenant,
            properties,
            references,
            validate_arguments,
        )

        self.__tenant = tenant
        self.__consistency_level = consistency_level
        self.__properties = properties
        self.__references = references

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        # Error: Cannot assign to attribute "with_tenant" for class "type[_CollectionBase[Properties@_CollectionBase, References@_CollectionBase]]*"
        # Attribute "with_tenant" is unknown (reportAttributeAccessIssue)
        cls.with_tenant = lambda self, tenant: _with_tenant(  # pyright: ignore
            cls,
            connection=cast(_CollectionBase, self)._connection,
            name=cast(_CollectionBase, self).name,
            validate_arguments=cast(_CollectionBase, self)._validate_arguments,
            consistency_level=cast(_CollectionBase, self).consistency_level,
            tenant=tenant.name if isinstance(tenant, Tenant) else tenant,
            properties=cast(_CollectionBase, self).__properties,
            references=cast(_CollectionBase, self).__references,
        )
        cls.with_consistency_level = (  # pyright: ignore
            lambda self, consistency_level: _with_consistency_level(
                cls,
                connection=cast(_CollectionBase, self)._connection,
                name=cast(_CollectionBase, self).name,
                validate_arguments=cast(_CollectionBase, self)._validate_arguments,
                consistency_level=consistency_level,
                tenant=cast(_CollectionBase, self).tenant,
                properties=cast(_CollectionBase, self).__properties,
                references=cast(_CollectionBase, self).__references,
            )
        )

    @property
    def tenant(self) -> Optional[str]:
        """The tenant of this collection object."""
        return self.__tenant

    @property
    def consistency_level(self) -> Optional[ConsistencyLevel]:
        """The consistency level of this collection object."""
        return self.__consistency_level
