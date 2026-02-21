import os
import sys

import django

project = "Steady Queue"
copyright = "2025, Elias Hernandis"
author = "Elias Hernandis"

# Make source available for autodoc
os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"
sys.path.insert(0, os.path.abspath(".."))
django.setup()

import steady_queue  # noqa: E402

release = steady_queue.__version__


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

templates_path = ["_templates"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]

html_theme_options = {
    "description": "A database-backed task backend for Django",
    "github_user": "knifecake",
    "github_repo": "steady-queue",
    "github_button": True,
    "github_type": "star",
}

# -- Napoleon extension configuration ----------------------------------------

napoleon_google_docstring = True
napoleon_numpy_docstring = False
