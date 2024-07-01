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


class TenantActivityStatusInput(str, Enum):
    """TenantActivityStatus class used to describe the activity status of a tenant in Weaviate.

    Attributes:
        `HOT`
            The tenant is fully active and can be used.
        `COLD`
            The tenant is not active, files stored locally.
    """

    HOT = "HOT"
    COLD = "COLD"


class TenantInput(BaseModel):
    """Tenant class used to describe a tenant in Weaviate.

    Attributes:
        `name`
            the name of the tenant.
        `activity_status`
            TenantActivityStatusInput, default: "HOT"
    """

    model_config = ConfigDict(populate_by_name=True)
    name: str
    activityStatus: TenantActivityStatusInput = Field(
        default=TenantActivityStatusInput.HOT, alias="activity_status"
    )

    @property
    def activity_status(self) -> TenantActivityStatusInput:
        """Getter for the activity status of the tenant."""
        return self.activityStatus
