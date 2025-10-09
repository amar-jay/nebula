# Configuration file for the Sphinx documentation builder.

# -- Project information

project = 'MATEK Nebula'
copyright = '2025, Apache'
author = 'amar-jay'

release = '0.1'
version = '1.0.0'

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'

# -- Options for EPUB output
epub_show_urls = 'footnote'


from docutils import nodes
from docutils.parsers.rst import roles
import re

def code_link_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    # Match text of the form "code <url>"
    match = re.match(r'(.+?)\s*<(.+?)>$', text)
    if match:
        label, url = match.groups()
        node = nodes.reference('', '', nodes.literal(label, label), refuri=url)
    else:
        # fallback: just render code if no URL provided
        node = nodes.literal(text, text)
    return [node], []

roles.register_local_role('c', code_link_role)