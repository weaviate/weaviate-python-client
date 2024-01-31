# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import contextlib
import os
import sys

from pkg_resources import DistributionNotFound, get_distribution

# -- Path setup --------------------------------------------------------------
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

sys.path.insert(0, os.path.abspath(".."))


@contextlib.contextmanager
def chdir(directory):
    curdir = os.curdir
    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(curdir)


try:
    dist = get_distribution("weaviate")
except DistributionNotFound:
    # The project is not installed in readthedocs environment. Read the version with setuptools_scm.
    import setuptools_scm

    with chdir(".."):
        release = setuptools_scm.get_version()
else:
    release = dist.version

# -- Project information -----------------------------------------------------

project = "Weaviate Python Client"
copyright = "2021-2024, Weaviate"
author = "Weaviate"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosectionlabel",
    "sphinxcontrib.autodoc_pydantic",
]

# Autodoc settings for pydantic
autodoc_pydantic_model_show_json = False
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_show_validator_summary = False
autodoc_pydantic_model_show_validator_members = False
autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_model_undoc_members = False
autodoc_pydantic_model_members = False


# Make sure the target is unique
autosectionlabel_prefix_document = True

autoclass_content = "both"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []
