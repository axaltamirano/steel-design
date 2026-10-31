"""Double angle (2L) shapes."""

from steel_design.materials.base import SteelMaterial
from steel_design.sections.database import DatabaseShape


class DoubleAngle(DatabaseShape):
    """Double angles, back to back (2L).

    `continuous_contact` records how the outstanding legs are connected: False (default) for
    angles with separators or intermittent connectors (Table B4.1a Case 3), True for angles
    connected with continuous contact (Table B4.1a Case 1).
    """

    family = "2L"

    def __init__(
        self,
        label: str,
        material: type[SteelMaterial] | None = None,
        continuous_contact: bool = False,
    ):
        """See :class:`DatabaseShape`; `continuous_contact` selects the Table B4.1a case."""
        super().__init__(label, material)
        self.continuous_contact = continuous_contact
