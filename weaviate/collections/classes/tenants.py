from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from weaviate.warnings import _Warnings


class _TenantActivistatusServerValues(str, Enum):
    """Values to be used when sending tenants to weaviate. Needed for BC."""

    HOT = "HOT"
    COLD = "COLD"
    FROZEN = "FROZEN"
    OTHER = "OTHER"  # placeholder for values that we receive from the server but do not send

    @staticmethod
    def from_string(value: str) -> "_TenantActivistatusServerValues":
        if value == "ACTIVE" or value == "HOT":
            return _TenantActivistatusServerValues.HOT
        if value == "INACTIVE" or value == "COLD":
            return _TenantActivistatusServerValues.COLD
        if value == "OFFLOADED" or value == "FROZEN":
            return _TenantActivistatusServerValues.FROZEN
        return _TenantActivistatusServerValues.OTHER


class TenantActivityStatus(str, Enum):
    """TenantActivityStatus class used to describe the activity status of a tenant in Weaviate.

    Attributes:
        `ACTIVE`
            The tenant is fully active and can be used.
        `INACTIVE`
            The tenant is not active, files stored locally.
        `OFFLOADED`
            The tenant is not active, files stored on the cloud.
        `OFFLOADING`
            The tenant is in the process of being offloaded.
        `ONLOADING`
            The tenant is in the process of being activated.
        `HOT`
            DEPRECATED, please use ACTIVE. The tenant is fully active and can be used.
        `COLD`
            DEPRECATED, please use INACTIVE. The tenant is not active, files stored locally.
        `FROZEN`
            DEPRECATED, please use OFFLOADED. The tenant is not active, files stored on the cloud.
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    OFFLOADED = "OFFLOADED"
    OFFLOADING = "OFFLOADING"
    ONLOADING = "ONLOADING"
    HOT = "HOT"
    COLD = "COLD"
    FROZEN = "FROZEN"


class Tenant(BaseModel):
    """Tenant class used to describe a tenant in Weaviate.

    Attributes:
        `name`
            the name of the tenant.
        `activity_status`
            TenantActivityStatus, default: "HOT"
    """

    model_config = ConfigDict(populate_by_name=True)
    name: str
    activityStatusInternal: TenantActivityStatus = Field(
        default=TenantActivityStatus.ACTIVE,
        alias="activity_status",
        exclude=True,
    )
    activityStatus: _TenantActivistatusServerValues = Field(
        init_var=False, default=_TenantActivistatusServerValues.HOT
    )

    @property
    def activity_status(self) -> TenantActivityStatus:
        """Getter for the activity status of the tenant."""
        return self.activityStatusInternal

    def model_post_init(self, __context: Any) -> None:  # noqa: D102
        self._model_post_init(user_input=True)

    def _model_post_init(self, user_input: bool) -> None:  # noqa: D102
        if self.activityStatusInternal == TenantActivityStatus.HOT:
            if user_input:
                _Warnings.deprecated_tenant_type("HOT", "ACTIVE")
            self.activityStatusInternal = TenantActivityStatus.ACTIVE
        elif self.activityStatusInternal == TenantUpdateActivityStatus.COLD:
            if user_input:
                _Warnings.deprecated_tenant_type("COLD", "INACTIVE")
            self.activityStatusInternal = TenantActivityStatus.INACTIVE
        elif self.activityStatusInternal == TenantUpdateActivityStatus.FROZEN:
            if user_input:
                _Warnings.deprecated_tenant_type("FROZEN", "OFFLOADED")
            self.activityStatusInternal = TenantActivityStatus.OFFLOADED
        if user_input:
            self.activityStatus = _TenantActivistatusServerValues.from_string(
                self.activityStatusInternal.value
            )


class TenantOutput(Tenant):  # noqa: D101
    """Wrapper around Tenant for output purposes."""

    def model_post_init(self, __context: Any) -> None:  # noqa: D102
        self._model_post_init(user_input=False)


class TenantCreateActivityStatus(str, Enum):
    """TenantActivityStatus class used to describe the activity status of a tenant to create in Weaviate.

    Attributes:
        `ACTIVE`
            The tenant is fully active and can be used.
        `INACTIVE`
            The tenant is not active, files stored locally.
        `HOT`
            DEPRECATED, please use ACTIVE. The tenant is fully active and can be used.
        `COLD`
            DEPRECATED, please use INACTIVE. The tenant is not active, files stored locally.
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    HOT = "HOT"
    COLD = "COLD"


class TenantUpdateActivityStatus(str, Enum):
    """TenantActivityStatus class used to describe the activity status of a tenant to update in Weaviate.

    Attributes:
        `ACTIVE`
            The tenant is fully active and can be used.
        `INACTIVE`
            The tenant is not active, files stored locally.
        `OFFLOADED`
            The tenant is not active, files stored on the cloud.
        `HOT`
            DEPRECATED, please use ACTIVE. The tenant is fully active and can be used.
        `COLD`
            DEPRECATED, please use INACTIVE. The tenant is not active, files stored locally.
        `FROZEN`
            DEPRECATED, please use OFFLOADED. The tenant is not active, files stored on the cloud.
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    OFFLOADED = "OFFLOADED"
    HOT = "HOT"
    COLD = "COLD"
    FROZEN = "FROZEN"


class TenantCreate(BaseModel):
    """Tenant class used to describe a tenant to create in Weaviate.

    Attributes:
        `name`
            the name of the tenant.
        `activity_status`
            TenantCreateActivityStatus, default: "HOT"
    """

    model_config = ConfigDict(populate_by_name=True)
    name: str
    activityStatusInternal: TenantCreateActivityStatus = Field(
        default=TenantCreateActivityStatus.ACTIVE,
        alias="activity_status",
        exclude=True,
    )
    activityStatus: _TenantActivistatusServerValues = Field(
        init_var=False, default=_TenantActivistatusServerValues.HOT
    )

    @property
    def activity_status(self) -> TenantCreateActivityStatus:
        """Getter for the activity status of the tenant."""
        return self.activityStatusInternal

    def model_post_init(self, __context: Any) -> None:  # noqa: D102
        if self.activityStatusInternal == TenantCreateActivityStatus.HOT:
            _Warnings.deprecated_tenant_type("HOT", "ACTIVE")
            self.activityStatusInternal = TenantCreateActivityStatus.ACTIVE
        elif self.activityStatusInternal == TenantCreateActivityStatus.COLD:
            _Warnings.deprecated_tenant_type("COLD", "INACTIVE")
            self.activityStatusInternal = TenantCreateActivityStatus.INACTIVE
        self.activityStatus = _TenantActivistatusServerValues.from_string(
            self.activityStatusInternal.value
        )


class TenantUpdate(BaseModel):
    """Tenant class used to describe a tenant to create in Weaviate.

    Attributes:
        `name`
            the name of the tenant.
        `activity_status`
            TenantUpdateActivityStatus, default: "HOT"
    """

    model_config = ConfigDict(populate_by_name=True)
    name: str
    activityStatusInternal: TenantUpdateActivityStatus = Field(
        default=TenantUpdateActivityStatus.ACTIVE, alias="activity_status", exclude=True
    )
    activityStatus: _TenantActivistatusServerValues = Field(
        init_var=False, default=_TenantActivistatusServerValues.HOT
    )

    @property
    def activity_status(self) -> TenantUpdateActivityStatus:
        """Getter for the activity status of the tenant."""
        return self.activityStatusInternal

    def model_post_init(self, __context: Any) -> None:  # noqa: D102
        if self.activityStatusInternal == TenantUpdateActivityStatus.HOT:
            _Warnings.deprecated_tenant_type("HOT", "ACTIVE")
            self.activityStatusInternal = TenantUpdateActivityStatus.ACTIVE
        elif self.activityStatusInternal == TenantUpdateActivityStatus.COLD:
            _Warnings.deprecated_tenant_type("COLD", "INACTIVE")
            self.activityStatusInternal = TenantUpdateActivityStatus.INACTIVE
        elif self.activityStatusInternal == TenantUpdateActivityStatus.FROZEN:
            _Warnings.deprecated_tenant_type("FROZEN", "OFFLOADED")
            self.activityStatusInternal = TenantUpdateActivityStatus.OFFLOADED
        self.activityStatus = _TenantActivistatusServerValues.from_string(
            self.activityStatusInternal.value
        )
