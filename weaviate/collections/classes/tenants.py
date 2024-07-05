from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from weaviate.warnings import _Warnings


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
        `ACTIVATING`
            The tenant is in the process of being activated.
        `HOT`
            DEPRECATED, please use ACTIVE. The tenant is fully active and can be used.
        `COLD`
            DEPRECATED, please use INACTIVE. The tenant is not active, files stored locally.
        `FROZEN`
            DEPRECATED, please use OFFLOADED. The tenant is not active, files stored on the cloud.
        `FREEZING`
            DEPRECATED, please use OFFLOADING. The tenant is in the process of being frozen.
        `UNFREEZING`
            DEPRECATED, please use ACTIVATING. The tenant is in the process of being unfrozen.
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    OFFLOADED = "OFFLOADED"
    OFFLOADING = "OFFLOADING"
    ACTIVATING = "ACTIVATING"
    HOT = "HOT"
    COLD = "COLD"
    FROZEN = "FROZEN"
    FREEZING = "FREEZING"
    UNFREEZING = "UNFREEZING"


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
    activityStatus: TenantActivityStatus = Field(
        default=TenantActivityStatus.ACTIVE, alias="activity_status"
    )

    @property
    def activity_status(self) -> TenantActivityStatus:
        """Getter for the activity status of the tenant."""
        return self.activityStatus

    def model_post_init(self, __context: Any) -> None:  # noqa: D102
        if self.activityStatus == TenantActivityStatus.HOT:
            _Warnings.deprecated_tenant_type("HOT", "ACTIVE")
            self.activityStatus = TenantActivityStatus.ACTIVE
        elif self.activityStatus == TenantUpdateActivityStatus.COLD:
            _Warnings.deprecated_tenant_type("COLD", "INACTIVE")
            self.activityStatus = TenantActivityStatus.INACTIVE
        elif self.activityStatus == TenantUpdateActivityStatus.FROZEN:
            _Warnings.deprecated_tenant_type("FROZEN", "OFFLOADED")
            self.activityStatus = TenantActivityStatus.OFFLOADED


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
    activityStatus: TenantCreateActivityStatus = Field(
        default=TenantCreateActivityStatus.ACTIVE, alias="activity_status"
    )

    @property
    def activity_status(self) -> TenantCreateActivityStatus:
        """Getter for the activity status of the tenant."""
        return self.activityStatus

    def model_post_init(self, __context: Any) -> None:  # noqa: D102
        if self.activityStatus == TenantCreateActivityStatus.HOT:
            _Warnings.deprecated_tenant_type("HOT", "ACTIVE")
            self.activityStatus = TenantCreateActivityStatus.ACTIVE
        elif self.activityStatus == TenantCreateActivityStatus.COLD:
            _Warnings.deprecated_tenant_type("COLD", "INACTIVE")
            self.activityStatus = TenantCreateActivityStatus.INACTIVE


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
    activityStatus: TenantUpdateActivityStatus = Field(
        default=TenantUpdateActivityStatus.ACTIVE, alias="activity_status"
    )

    @property
    def activity_status(self) -> TenantUpdateActivityStatus:
        """Getter for the activity status of the tenant."""
        return self.activityStatus

    def model_post_init(self, __context: Any) -> None:  # noqa: D102
        if self.activityStatus == TenantUpdateActivityStatus.HOT:
            _Warnings.deprecated_tenant_type("HOT", "ACTIVE")
            self.activityStatus = TenantUpdateActivityStatus.ACTIVE
        elif self.activityStatus == TenantUpdateActivityStatus.COLD:
            _Warnings.deprecated_tenant_type("COLD", "INACTIVE")
            self.activityStatus = TenantUpdateActivityStatus.INACTIVE
        elif self.activityStatus == TenantUpdateActivityStatus.FROZEN:
            _Warnings.deprecated_tenant_type("FROZEN", "OFFLOADED")
            self.activityStatus = TenantUpdateActivityStatus.OFFLOADED
