import datetime
import uuid as uuid_package

from typing import Any, Dict, List, Literal, Mapping, Optional, Sequence, Type, Union, get_origin
from typing_extensions import TypeAlias, TypeVar, is_typeddict

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core.core_schema import FieldValidationInfo
from pydantic_extra_types import phone_numbers

from weaviate.exceptions import InvalidDataModelException


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

    @field_validator("number")
    def _validate_number(cls, v: str, info: FieldValidationInfo) -> str:
        return phone_numbers.PhoneNumber._validate(v, info)


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
    List[str],  # text[]
    List[bool],  # boolean[]
    List[int],  # int[]
    List[float],  # number[]
    List[datetime.datetime],  # date[]
    List[uuid_package.UUID],  # uuid[]
    Sequence[Mapping[str, "WeaviateField"]],  # object[]
    # Sequence is covariant while List is not, so we use Sequence here to allow for
    # List[Dict[str, WeaviateField]] to be used interchangeably with List[Dict[str, Any]]
]

WeaviateProperties: TypeAlias = Mapping[str, WeaviateField]
# current limitation of mypy is that Dict[str, WeaviateField] is not successfully inferred
# when used in DataObject. It can't understand that DataObject[Dict[str, str], None] is covariant
# with DataObject[Dict[str, WeaviateField], None]

SHARD_TYPES = Literal["READONLY", "READY", "INDEXING"]


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


def _check_properties_generic(properties: Optional[Type[Properties]]) -> None:
    if (
        properties is not None
        and get_origin(properties) is not dict
        and not is_typeddict(properties)
    ):
        raise InvalidDataModelException("properties")


ISOCountryCode = Literal[
    "AD",
    "AE",
    "AF",
    "AG",
    "AI",
    "AL",
    "AM",
    "AO",
    "AQ",
    "AR",
    "AS",
    "AT",
    "AU",
    "AW",
    "AX",
    "AZ",
    "BA",
    "BB",
    "BD",
    "BE",
    "BF",
    "BG",
    "BH",
    "BI",
    "BJ",
    "BL",
    "BM",
    "BN",
    "BO",
    "BQ",
    "BR",
    "BS",
    "BT",
    "BV",
    "BW",
    "BY",
    "BZ",
    "CA",
    "CC",
    "CD",
    "CF",
    "CG",
    "CH",
    "CI",
    "CK",
    "CL",
    "CM",
    "CN",
    "CO",
    "CR",
    "CU",
    "CV",
    "CW",
    "CX",
    "CY",
    "CZ",
    "DE",
    "DJ",
    "DK",
    "DM",
    "DO",
    "DZ",
    "EC",
    "EE",
    "EG",
    "EH",
    "ER",
    "ES",
    "ET",
    "FI",
    "FJ",
    "FK",
    "FM",
    "FO",
    "FR",
    "GA",
    "GB",
    "GD",
    "GE",
    "GF",
    "GG",
    "GH",
    "GI",
    "GL",
    "GM",
    "GN",
    "GP",
    "GQ",
    "GR",
    "GS",
    "GT",
    "GU",
    "GW",
    "GY",
    "HK",
    "HM",
    "HN",
    "HR",
    "HT",
    "HU",
    "ID",
    "IE",
    "IL",
    "IM",
    "IN",
    "IO",
    "IQ",
    "IR",
    "IS",
    "IT",
    "JE",
    "JM",
    "JO",
    "JP",
    "KE",
    "KG",
    "KH",
    "KI",
    "KM",
    "KN",
    "KP",
    "KR",
    "KW",
    "KY",
    "KZ",
    "LA",
    "LB",
    "LC",
    "LI",
    "LK",
    "LR",
    "LS",
    "LT",
    "LU",
    "LV",
    "LY",
    "MA",
    "MC",
    "MD",
    "ME",
    "MF",
    "MG",
    "MH",
    "MK",
    "ML",
    "MM",
    "MN",
    "MO",
    "MP",
    "MQ",
    "MR",
    "MS",
    "MT",
    "MU",
    "MV",
    "MW",
    "MX",
    "MY",
    "MZ",
    "NA",
    "NC",
    "NE",
    "NF",
    "NG",
    "NI",
    "NL",
    "NO",
    "NP",
    "NR",
    "NU",
    "NZ",
    "OM",
    "PA",
    "PE",
    "PF",
    "PG",
    "PH",
    "PK",
    "PL",
    "PM",
    "PN",
    "PR",
    "PS",
    "PT",
    "PW",
    "PY",
    "QA",
    "RE",
    "RO",
    "RS",
    "RU",
    "RW",
    "SA",
    "SB",
    "SC",
    "SD",
    "SE",
    "SG",
    "SH",
    "SI",
    "SJ",
    "SK",
    "SL",
    "SM",
    "SN",
    "SO",
    "SR",
    "SS",
    "ST",
    "SV",
    "SX",
    "SY",
    "SZ",
    "TC",
    "TD",
    "TF",
    "TG",
    "TH",
    "TJ",
    "TK",
    "TL",
    "TM",
    "TN",
    "TO",
    "TR",
    "TT",
    "TV",
    "TW",
    "TZ",
    "UA",
    "UG",
    "UM",
    "US",
    "UY",
    "UZ",
    "VA",
    "VC",
    "VE",
    "VG",
    "VI",
    "VN",
    "VU",
    "WF",
    "WS",
    "YE",
    "YT",
    "ZA",
    "ZM",
    "ZW",
]
