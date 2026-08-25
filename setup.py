# coding=utf-8
from setuptools import setup

plugin_identifier = "potatorelay"
plugin_package = "octoprint_potatorelay"
plugin_name = "OctoPrint-PotatoRelay"
plugin_version = "0.1.0"
plugin_description = (
    "Control up to 8 relays via GPIO on a Libre Computer 'Le Potato' "
    "(AML-S905X-CC) using libregpio. OctoRelay-style feature set: "
    "custom icons/labels, navbar buttons, GCODE commands, REST API, "
    "printer-relay autoconnect, event-based automation, OS command side effects."
)
plugin_author = "Miles Hilliard"
plugin_author_email = "miles@mileshilliard.com"
plugin_url = "https://github.com/syntaxerror019/octoprint-potatorelay"
plugin_license = "AGPLv3"
plugin_requires = []

plugin_additional_data = []
plugin_additional_packages = []
plugin_additional_stuff = []

try:
    import octoprint_setuptools
except ImportError:
    print("Could not import OctoPrint's setuptools, are you sure you are running that under "
          "the same python installation that OctoPrint is installed under?")
    import sys
    sys.exit(-1)

setup_parameters = octoprint_setuptools.create_plugin_setup_parameters(
    identifier=plugin_identifier,
    package=plugin_package,
    name=plugin_name,
    version=plugin_version,
    description=plugin_description,
    author=plugin_author,
    mail=plugin_author_email,
    url=plugin_url,
    license=plugin_license,
    requires=plugin_requires,
    additional_packages=plugin_additional_packages,
    ignored_packages=[],
    additional_data=plugin_additional_data,
)

setup(**setup_parameters)
