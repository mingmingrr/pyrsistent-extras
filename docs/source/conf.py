project          = 'pyrsistent-extras'
copyright        = '2024, mingmingrr'
author           = 'mingmingrr'
templates_path   = ['_templates']
exclude_patterns = []

extensions = [
	'sphinx.ext.autodoc',
	#  'sphinx.ext.autosummary',
	'sphinx.ext.mathjax',
	'sphinx.ext.intersphinx',
	'sphinx.ext.viewcode',
	'sphinx_autodoc_typehints',
]

autodoc_typehints = 'both'
autodoc_docstring_signature = True

intersphinx_mapping = {
	'python': ('https://docs.python.org/3', None),
	'pyrsistent': ('https://pyrsistent.readthedocs.io/en/latest', None),
}

import sphinx_rtd_theme
html_theme      = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

import builtins
builtins.__sphinx_build__ = True

