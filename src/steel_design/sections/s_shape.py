"""American standard beam (S) shapes."""

from steel_design.sections.database import DatabaseShape


class SShape(DatabaseShape):
    """American standard beams."""

    family = "S"
