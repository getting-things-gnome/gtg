#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# Use local version of GTG
sys.path.insert(0, '../..')

from GTG import info

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.graphviz',
    'sphinx.ext.viewcode',
]

project = 'Getting Things GNOME!'
copyright = 'The GTG Team'

short_version = '.'.join(info.VERSION.split('.')[:2])
version = short_version
release = info.VERSION

master_doc = 'index'
source_suffix = '.rst'

exclude_patterns = []
pygments_style = 'sphinx'

# -- Options for HTML output ----------------------------------------------
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if on_rtd:
    html_theme = 'default'
else:
    html_theme = 'nature'

html_show_sphinx = False

# -- Options for LaTeX output ---------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [(
    'index',
    'gtg.tex',
    'Getting Things GNOME! Documentation',
    'The GTG Team',
    'manual',
)]

# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (
        'man/gtcli', 'gtcli',
        'Command-line interface for Getting Things GNOME!',
        [], 1,
    ),
    (
        'man/gtg', 'gtg',
        'Getting Things GNOME!, a personal tasks and TODO-list items '
        'organizer for the GNOME desktop environment',
        [], 1,
    ),
    (
        'man/gtg_new_task', 'gtg_new_task',
        'Adds a task to the Getting Things GNOME! organizer',
        [], 1,
    ),
]
