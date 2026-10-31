"""Sphinx configuration for the steel-design documentation."""

project = "steel-design"
author = "steel-design contributors"
copyright = "2025, steel-design contributors"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pint": ("https://pint.readthedocs.io/en/stable", None),
}
autodoc_member_order = "bysource"
autodoc_typehints = "description"
source_suffix = {".md": "markdown"}
exclude_patterns = ["_build"]
html_theme = "furo"
html_static_path = ["_static"]
