from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class TenantActivityStatus(str, Enum):
    """TenantActivityStatus class used to describe the activity status of a tenant in Weaviate.

    Attributes:
        `HOT`
            The tenant is fully active and can be used.
        `COLD`
            The tenant is not active, files stored locally.
        `FROZEN`
            The tenant is not active, files stored on the cloud.
        `FREEZING`
            The tenant is in the process of being frozen.
        `UNFREEZING`
            The tenant is in the process of being unfrozen.
        `UNFROZEN`
            The tenant has been pulled from the cloud and is not yet active nor inactive.
    """

    HOT = "HOT"
    COLD = "COLD"
    FROZEN = "FROZEN"
    FREEZING = "FREEZING"
    UNFREEZING = "UNFREEZING"
    UNFROZEN = "UNFROZEN"


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
        default=TenantActivityStatus.HOT, alias="activity_status"
    )

    @property
    def activity_status(self) -> TenantActivityStatus:
        """Getter for the activity status of the tenant."""
        return self.activityStatus


class TenantCreateActivityStatus(str, Enum):
    """TenantActivityStatus class used to describe the activity status of a tenant to create in Weaviate.

    Attributes:
        `HOT`
            The tenant is fully active and can be used.
        `COLD`
            The tenant is not active, files stored locally.
    """

    HOT = "HOT"
    COLD = "COLD"


class TenantUpdateActivityStatus(str, Enum):
    """TenantActivityStatus class used to describe the activity status of a tenant to update in Weaviate.

    Attributes:
        `HOT`
            The tenant is fully active and can be used.
        `COLD`
            The tenant is not active, files stored locally.
        `FROZEN`
            The tenant is not active, files stored on the cloud.
    """

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
        default=TenantCreateActivityStatus.HOT, alias="activity_status"
    )

    @property
    def activity_status(self) -> TenantCreateActivityStatus:
        """Getter for the activity status of the tenant."""
        return self.activityStatus


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
        default=TenantUpdateActivityStatus.HOT, alias="activity_status"
    )

    @property
    def activity_status(self) -> TenantUpdateActivityStatus:
        """Getter for the activity status of the tenant."""
        return self.activityStatus
