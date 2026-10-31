"""Steel pipe shapes."""

from steel_design.sections.database import DatabaseShape


class Pipe(DatabaseShape):
    """Steel pipe."""

    family = "PIPE"
