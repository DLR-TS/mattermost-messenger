#
# Copyright (C) DLR-TS 2024, 2025
#
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


import importlib.metadata


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Mattermost Messenger'
copyright = 'DLR 2024, 2025'
author = 'Björn Hendriks'
# Get version from pyproject.toml
version = importlib.metadata.version('mattermost-messenger')
release = version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'myst_nb',
    'autoapi.extension',
    'sphinx.ext.viewcode',
    'sphinx.ext.autodoc',
]

autoapi_dirs = ['../mattermost_messenger']
## Include both class docstrings and __init__ docstrings
autoapi_python_class_content = 'both'
## Set autoapi_keep_files to True to see intermediate doc files
# autoapi_keep_files = True

## Include type hints in autoapi-generated docs
autodoc_typehints = 'description'

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
