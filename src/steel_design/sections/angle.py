"""Single angle (L) shapes from the AISC Shapes Database."""

from steel_design.sections.database import DatabaseShape


class Angle(DatabaseShape):
    """Single angles."""

    family = "L"
