# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import contextlib
import os
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as version_func

# -- Path setup --------------------------------------------------------------
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

sys.path.insert(0, os.path.abspath(".."))

# weaviate-agents-python-client as a sub-library (cloned into docs/)
sys.path.insert(0, os.path.abspath("weaviate-agents-python-client"))


@contextlib.contextmanager
def chdir(directory):
    curdir = os.curdir
    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(curdir)


try:
    version = version_func("weaviate")
except PackageNotFoundError:
    # The project is not installed in readthedocs environment. Read the version with setuptools_scm.
    import setuptools_scm

    with chdir(".."):
        release = setuptools_scm.get_version()


# -- Project information -----------------------------------------------------

project = "Weaviate Python Client"
copyright = "2021-2025, Weaviate"
author = "Weaviate"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.napoleon",
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

autodoc_typehints = "description"
autodoc_member_order = "bysource"
autodoc_dataclass_fields = False

# Make sure the target is unique
autosectionlabel_prefix_document = True

autoclass_content = "both"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "README.rst"]

suppress_warnings = [
    "docutils",
    "autodoc",
    "autosectionlabel",
]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

html_theme_options = {"navigation_depth": 10}  # Increase this to match `toctree`

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

import re


def convert_markdown_links(lines):
    """Convert Markdown-style [text](url) links to reST-style `text <url>`_ links."""
    md_link_pattern = re.compile(r"\[([^\]]+)\]\((http[^\)]+)\)")
    return [md_link_pattern.sub(r"`\1 <\2>`_", line) for line in lines]


def replace_client_parent_docstring_to_match_child(what, obj, lines):
    """Replace the parent class docstring with the child class docstring."""
    if what != "class" or not obj.__name__ in ("WeaviateClient", "WeaviateAsyncClient"):
        return lines

    # Replace Parent class's "WeaviateClient/WeaviateClientAsync" with the child class's name
    text = "\n".join(lines)
    text = text.replace("WeaviateClient/WeaviateClientAsync", obj.__name__)

    # Make the connect_to function references into links to actual functions
    pattern = re.compile(r"\b(weaviate\.connect_to_[a-zA-Z_][a-zA-Z0-9_]*)\b")
    text = pattern.sub(r":func:`\1`", text)

    # Rename the connect_to function to use_async_with for the WeaviateAsyncClient
    if obj.__name__ == "WeaviateAsyncClient":
        text = text.replace("connect_to", "use_async_with")

    return text.split("\n")


def shorthand_weaviate_exceptions_display(lines):
    """Replace weaviate.exceptions.* with ~weaviate.exceptions.* to make it a shorthand."""
    pattern = re.compile(r"\b(weaviate\.exceptions\.[a-zA-Z_][a-zA-Z0-9_]*)\b")
    return [pattern.sub(r"~\1", line) for line in lines]


def autodoc_process_docstring(app, what, name, obj, options, lines):
    """Apply the conversion to all docstrings."""
    lines[:] = convert_markdown_links(lines)
    lines[:] = replace_client_parent_docstring_to_match_child(what, obj, lines)
    lines[:] = shorthand_weaviate_exceptions_display(lines)


def setup(app):
    app.add_css_file("custom.css")
    app.connect("autodoc-process-docstring", autodoc_process_docstring)
