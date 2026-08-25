# coding=utf-8
from setuptools import setup

plugin_identifier = "octorelay_lepotato"
plugin_package = "octoprint_octorelay_lepotato"
plugin_name = "OctoPrint-OctoRelay-LePotato"
plugin_version = "0.1.0"
plugin_description = (
    "Control up to 8 relays via GPIO on a Libre Computer 'Le Potato' "
    "(AML-S905X-CC) using libregpio. OctoRelay-style feature set: "
    "custom icons/labels, navbar buttons, GCODE commands, REST API, "
    "printer-relay autoconnect, event-based automation, OS command side effects."
)
plugin_author = "You"
plugin_author_email = "you@example.com"
plugin_url = "https://github.com/YOURUSER/OctoRelay-LePotato"
plugin_license = "AGPLv3"
plugin_requires = ["libregpio"]

plugin_additional_data = []
plugin_additional_packages = []
plugin_additional_stuff = []

setup(
    name=plugin_name,
    version=plugin_version,
    description=plugin_description,
    author=plugin_author,
    author_email=plugin_author_email,
    url=plugin_url,
    license=plugin_license,
    packages=[plugin_package],
    include_package_data=True,
    install_requires=plugin_requires,
    entry_points={
        "octoprint.plugin": [
            "{} = {}".format(plugin_identifier, plugin_package)
        ]
    },
)
