import os, sys
sys.path.insert(0, os.path.abspath("../../src"))

project = "raster2poly"
copyright = "2026, Ismail Harkat"
author = "Ismail Harkat"
version = release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "nbsphinx",
]

autosummary_generate = True
autodoc_typehints = "description"
autodoc_member_order = "bysource"
napoleon_numpy_docstring = True
napoleon_use_param = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "geopandas": ("https://geopandas.org/en/stable/", None),
    "sklearn": ("https://scikit-learn.org/stable/", None),
}

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
exclude_patterns = ["_build"]

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 3,
    "collapse_navigation": False,
}
html_static_path = []
html_title = f"{project} {version}"

# nbsphinx
nbsphinx_execute = "never"
nbsphinx_allow_errors = True
