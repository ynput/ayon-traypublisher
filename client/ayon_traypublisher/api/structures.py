from dataclasses import dataclass
from typing import Any, Literal

DataType = Literal["version_data", "representation_data", "instance_data"]


@dataclass
class PassingDataValue:
    """Represents a value to be passed to the publishing context.

    This class encapsulates values that need to be passed to the traypublisher
    publishing context. Data values are mapped from settings column
    configurations to instances of this object for inclusion in version,
    representation, or instance data.
    """

    name: str
    value: Any
    data_type: DataType = "version_data"
