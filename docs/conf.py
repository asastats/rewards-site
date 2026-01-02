# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

import os
import subprocess
import sys

import django

sys.path.insert(0, os.path.abspath("../rewardsweb"))

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

# Set Django settings
os.environ["DJANGO_SETTINGS_MODULE"] = "rewardsweb.settings.development"


django.setup()


# -- Project information -----------------------------------------------------

project = "Rewards Suite"
copyright = "2026, ASA Stats DAO"
authors = "Eduard Ravnic and Ivica Paleka"

# The full version, including alpha/beta/rc tags
from rewardsweb import __version__

release = __version__

# -- General configuration ---------------------------------------------------

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
source_suffix = [".rst", ".md"]

master_doc = "index"

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "myst_parser",
]

# Generate TypeDoc documentation if not on ReadTheDocs
if not os.environ.get("READTHEDOCS"):
    frontend_path = os.path.abspath("../rewardsweb/frontend")
    if os.path.exists(frontend_path):
        print("Generating TypeDoc documentation...")
        try:
            subprocess.run(
                ["npm", "run", "docs"],
                cwd=frontend_path,
                check=True,
            )
            # Delete generated README.md and modules.md files
            import glob

            for file_path in glob.glob(
                os.path.join(
                    project_root, "docs", "api", "frontend_api", "**", "README.md"
                ),
                recursive=True,
            ):
                os.remove(file_path)
            for file_path in glob.glob(
                os.path.join(
                    project_root, "docs", "api", "frontend_api", "**", "modules.md"
                ),
                recursive=True,
            ):
                os.remove(file_path)
            # Remove cross-references to README.md from other generated .md files
            for root, dirs, files in os.walk(
                os.path.join(project_root, "docs", "api", "frontend_api")
            ):
                for file in files:
                    if (
                        file.endswith(".md")
                        and file != "README.md"
                        and file != "modules.md"
                    ):
                        filepath = os.path.join(root, file)
                        with open(filepath, "r") as f:
                            lines = f.readlines()
                        with open(filepath, "w") as f:
                            for line in lines:
                                if (
                                    "../../README.md" not in line
                                    and "../README.md" not in line
                                ):
                                    f.write(line)
                        # Remove leading horizontal rules or other transitions
                        with open(filepath, "r") as f:
                            lines = f.readlines()

                        # Define a list of common reStructuredText transition markers
                        transition_markers = [
                            "---",
                            "===",
                            "***",
                            "___",
                            "+++",
                            "~~~",
                            "^^^",
                            "```",
                        ]

                        # Filter out leading transition lines
                        filtered_lines = []
                        transition_found = False
                        for line in lines:
                            if (
                                not transition_found
                                and line.strip() in transition_markers
                            ):
                                transition_found = True
                                continue
                            filtered_lines.append(line)

                        with open(filepath, "w") as f:
                            f.writelines(filtered_lines)
        except subprocess.CalledProcessError:
            print("TypeDoc generation failed - continuing without frontend docs")

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
html_static_path = ["_static"]


html_logo = "_static/logo.png"
html_favicon = "_static/favicon.ico"

latex_documents = [
    (
        "index",
        "asastats-rewards-suite.tex",
        "Rewards Suite documentation",
        authors,
        "howto",
    )
]
