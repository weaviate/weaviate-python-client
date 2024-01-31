import datetime
import uuid as uuid_package

from typing import Any, Dict, Mapping, Optional, Sequence, Type, Union, get_origin
from typing_extensions import TypeAlias, TypeVar, is_typeddict

from pydantic import BaseModel, ConfigDict, Field

from weaviate.exceptions import InvalidDataModelError


class _WeaviateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GeoCoordinate(_WeaviateInput):
    """Input for the geo-coordinate datatype."""

    latitude: float = Field(default=..., le=90, ge=-90)
    longitude: float = Field(default=..., le=180, ge=-180)

    def _to_dict(self) -> Dict[str, float]:
        return self.model_dump(exclude_none=True)


class _PhoneNumberBase(_WeaviateInput):
    number: str


class PhoneNumber(_PhoneNumberBase):
    """Input for the phone number datatype.

    `default_country` should correspond to the ISO 3166-1 alpha-2 country code.
    This is used to figure out the correct countryCode and international format if only a national number (e.g. 0123 4567) is provided.
    """

    default_country: Optional[str] = Field(default=None)

    def _to_dict(self) -> Mapping[str, str]:
        out: Dict[str, str] = {"input": self.number}
        if self.default_country is not None:
            out["defaultCountry"] = self.default_country
        return out


class _PhoneNumber(_PhoneNumberBase):
    """Output for the phone number datatype."""

    country_code: int
    default_country: str
    international_formatted: str
    national: int
    national_formatted: str
    valid: bool


PhoneNumberType: TypeAlias = _PhoneNumber


WeaviateField: TypeAlias = Union[
    None,  # null
    str,  # text
    bool,  # boolean
    int,  # int
    float,  # number
    datetime.datetime,  # date
    uuid_package.UUID,  # uuid
    GeoCoordinate,  # geoCoordinates
    Union[PhoneNumber, PhoneNumberType],  # phoneNumber
    Mapping[str, "WeaviateField"],  # object
    Sequence[str],  # text[]
    Sequence[bool],  # boolean[]
    Sequence[int],  # int[]
    Sequence[float],  # number[]
    Sequence[datetime.datetime],  # date[]
    Sequence[uuid_package.UUID],  # uuid[]
    Sequence[Mapping[str, "WeaviateField"]],  # object[]
    # Sequence is covariant while List is not, so we use Sequence here to allow for
    # List[Dict[str, WeaviateField]] to be used interchangeably with List[Dict[str, Any]]
]

WeaviateProperties: TypeAlias = Mapping[str, WeaviateField]

Properties = TypeVar("Properties", bound=Mapping[str, Any], default=WeaviateProperties)
"""`Properties` is used wherever a single generic type is needed for properties"""

TProperties = TypeVar("TProperties", bound=Mapping[str, Any], default=WeaviateProperties)
"""`TProperties` is used alongside `Properties` wherever there are two generic types needed

E.g., in `_DataCollection`, `Properties` is used when defining the generic of the class while
`TProperties` is used when defining the generic to be supplied in `.with_data_model` to create
a new instance of `_DataCollection` with a different `Properties` type.

To be clear: `_DataCollection[Properties]().with_data_model(TProperties) -> _DataCollection[TProperties]()`
"""

DProperties = TypeVar("DProperties", bound=Mapping[str, Any], default=Dict[str, Any])
QProperties = TypeVar("QProperties", bound=Mapping[str, Any], default=WeaviateProperties)

NProperties = TypeVar("NProperties", bound=Optional[Mapping[str, Any]], default=None)

M = TypeVar("M")
"""`M` is a completely general type that is used wherever generic metadata objects are defined that can be used"""

P = TypeVar("P")
"""`P` is a completely general type that is used wherever generic properties objects are defined that can be used
within the non-ORM and ORM APIs interchangeably"""

QP = TypeVar("QP")
"""`QP` is a completely general type that is used wherever generic properties objects are defined that can be used
within the non-ORM and ORM APIs interchangeably"""

R = TypeVar("R")
"""`R` is a completely general type that is used wherever generic reference objects are defined that can be used
within the non-ORM and ORM APIs interchangeably"""

QR = TypeVar("QR")
"""`QR` is a completely general type that is used wherever generic reference objects are defined that can be used
within the non-ORM and ORM APIs interchangeably"""

T = TypeVar("T")
"""`T` is a completely general type that is used in any kind of generic"""

References = TypeVar("References", bound=Optional[Mapping[str, Any]], default=None)
"""`References` is used wherever a single generic type is needed for references"""

IReferences = TypeVar("IReferences", bound=Optional[Mapping[str, Any]], default=None)

# I wish we could have bound=Mapping[str, CrossReference["P", "R"]] here, but you can't have generic bounds, so Any must suffice
TReferences = TypeVar("TReferences", bound=Optional[Mapping[str, Any]], default=None)
"""`TReferences` is used alongside `References` wherever there are two generic types needed"""


def _check_properties_generic(properties: Optional[Type[Properties]]) -> None:
    if (
        properties is not None
        and get_origin(properties) is not dict
        and not is_typeddict(properties)
    ):
        raise InvalidDataModelError("properties")


def _check_references_generic(references: Optional[Type["References"]]) -> None:
    if (
        references is not None
        and get_origin(references) is not dict
        and not is_typeddict(references)
    ):
        raise InvalidDataModelError("references")
