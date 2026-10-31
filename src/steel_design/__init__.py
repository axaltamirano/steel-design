"""Python implementation of AISC 360-22 steel design provisions (US customary units)."""

from steel_design.units import Q_, ureg


def main() -> None:
    """Console-script entry point; currently only prints a usage hint."""
    print("steel-design: import the library to use it (see README).")


__all__ = ["Q_", "ureg", "main"]
