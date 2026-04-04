# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import sys
import os

sys.path.append(os.path.abspath('../../'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fine_project.settings')

import django

django.setup()

project = 'FinE'
copyright = '2023, os101_04'
author = 'os101_04'
release = 'v0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
]

templates_path = ['_templates']
exclude_patterns = []

language = 'ru'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
intersphinx_mapping = {
    'django': (
        'http://docs.djangoproject.com/en/dev/',
        'http://docs.djangoproject.com/en/dev/_objects/',
    )
}
