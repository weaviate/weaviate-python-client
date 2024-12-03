from typing import Optional, Union, Sequence

from weaviate.cluster.types import Verbosity
from weaviate.rbac.models import (
    _Permission,
    _DataPermission,
    DataAction,
    _CollectionsPermission,
    CollectionsAction,
    _RolesPermission,
    RolesAction,
    _UsersPermission,
    UsersAction,
    _ClusterPermission,
    ClusterAction,
    _NodesPermission,
    NodesAction,
    _BackupsPermission,
    BackupsAction,
)

PermissionsType = Union[_Permission, Sequence[_Permission], Sequence[Sequence[_Permission]]]


class _DataFactory:
    @staticmethod
    def create(*, collection: str) -> _DataPermission:
        return _DataPermission(
            collection=collection, tenant="*", object_="*", action=DataAction.CREATE
        )

    @staticmethod
    def read(*, collection: str) -> _DataPermission:
        return _DataPermission(
            collection=collection, tenant="*", object_="*", action=DataAction.READ
        )

    @staticmethod
    def update(*, collection: str) -> _DataPermission:
        return _DataPermission(
            collection=collection, tenant="*", object_="*", action=DataAction.UPDATE
        )

    @staticmethod
    def delete(*, collection: str) -> _DataPermission:
        return _DataPermission(
            collection=collection, tenant="*", object_="*", action=DataAction.DELETE
        )

    @staticmethod
    def manage(*, collection: str) -> _DataPermission:
        return _DataPermission(
            collection=collection, tenant="*", object_="*", action=DataAction.MANAGE
        )


class _CollectionsFactory:
    @staticmethod
    def create(*, collection: Optional[str] = None) -> _CollectionsPermission:
        return _CollectionsPermission(
            collection=collection or "*", tenant="*", action=CollectionsAction.CREATE
        )

    @staticmethod
    def read(*, collection: Optional[str] = None) -> _CollectionsPermission:
        return _CollectionsPermission(
            collection=collection or "*", tenant="*", action=CollectionsAction.READ
        )

    @staticmethod
    def update(*, collection: Optional[str] = None) -> _CollectionsPermission:
        return _CollectionsPermission(
            collection=collection or "*", tenant="*", action=CollectionsAction.UPDATE
        )

    @staticmethod
    def delete(*, collection: Optional[str] = None) -> _CollectionsPermission:
        return _CollectionsPermission(
            collection=collection or "*", tenant="*", action=CollectionsAction.DELETE
        )

    @staticmethod
    def manage(*, collection: Optional[str] = None) -> _CollectionsPermission:
        return _CollectionsPermission(
            collection=collection or "*", tenant="*", action=CollectionsAction.MANAGE
        )


class _RolesFactory:
    @staticmethod
    def manage(*, role: Optional[str] = None) -> _RolesPermission:
        return _RolesPermission(role=role or "*", action=RolesAction.MANAGE)

    @staticmethod
    def read(*, role: Optional[str] = None) -> _RolesPermission:
        return _RolesPermission(role=role or "*", action=RolesAction.READ)


class _UsersFactory:
    @staticmethod
    def manage() -> _UsersPermission:
        return _UsersPermission(action=UsersAction.MANAGE)


class _ClusterFactory:
    @staticmethod
    def read() -> _ClusterPermission:
        return _ClusterPermission(action=ClusterAction.READ)


class _NodesFactory:
    @staticmethod
    def read(
        *, collection: Optional[str] = None, verbosity: Verbosity = "minimal"
    ) -> _NodesPermission:
        return _NodesPermission(
            collection=collection or "*", action=NodesAction.READ, verbosity=verbosity
        )


class _BackupsFactory:
    @staticmethod
    def manage(*, collection: Optional[str] = None) -> _BackupsPermission:
        return _BackupsPermission(collection=collection or "*", action=BackupsAction.MANAGE)


class Permissions:

    @staticmethod
    def data(
        *,
        collection: str,
        create: bool = False,
        read: bool = False,
        update: bool = False,
        delete: bool = False,
        manage: bool = False
    ) -> Sequence[PermissionsType]:
        permissions = []
        if create:
            permissions.append(_DataFactory.create(collection=collection))
        if read:
            permissions.append(_DataFactory.read(collection=collection))
        if update:
            permissions.append(_DataFactory.update(collection=collection))
        if delete:
            permissions.append(_DataFactory.delete(collection=collection))
        if manage:
            permissions.append(_DataFactory.manage(collection=collection))
        return permissions

    @staticmethod
    def collection_config(
        *,
        collection: str,
        create_collection: bool = False,
        read_config: bool = False,
        update_config: bool = False,
        delete_collection: bool = False,
            manage_collection: bool = False
    ) -> Sequence[PermissionsType]:
        permissions = []
        if create_collection:
            permissions.append(_CollectionsFactory.create(collection=collection))
        if read_config:
            permissions.append(_CollectionsFactory.read(collection=collection))
        if update_config:
            permissions.append(_CollectionsFactory.update(collection=collection))
        if delete_collection:
            permissions.append(_CollectionsFactory.delete(collection=collection))
        if manage_collection:
            permissions.append(_CollectionsFactory.manage(collection=collection))
        return permissions

    @staticmethod
    def roles(*, role: str, read: bool = False, manage: bool = False) -> Sequence[PermissionsType]:
        permissions = []
        if read:
            permissions.append(_RolesFactory.read(role=role))
        if manage:
            permissions.append(_RolesFactory.read(role=role))
        return permissions

    @staticmethod
    def backup(*, collection: str, manage: bool = False) -> Sequence[PermissionsType]:
        permissions = []
        if manage:
            permissions.append(_BackupsFactory.manage(collection=collection))
        return permissions

    @staticmethod
    def nodes(
        *, collection: str, verbosity: Verbosity = "minimal", read: bool = False
    ) -> Sequence[PermissionsType]:
        permissions = []
        if read:
            permissions.append(_NodesFactory.read(collection=collection, verbosity=verbosity))
        return permissions

    @staticmethod
    def cluster(*, read: bool = False) -> Sequence[PermissionsType]:
        permissions = []
        if read:
            permissions.append(_ClusterFactory.read())
        return permissions


class RBAC:
    permissions = Permissions
