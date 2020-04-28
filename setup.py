from setuptools import setup
import sys

if sys.version_info.major <= 2:
    sys.stderr.write("Python >=3 required (detected: %s.%s.x)" % (
        sys.version_info.major,
        sys.version_info.minor
    ))
    exit(1)

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="wsl-windows-toolbar",
    version="0.2",
    author="Frank Quinn",
    author_email="fquinn@cascadium.io",
    description="Adds linux GUI application menu to a windows toolbar",
    long_description=long_description,
    url="http://cascadium.io",
    python_requires='>=3',
    install_requires=[
        "click",
        "pyxdg",
        "winshell",
        "swinlnk",
        "pillow",
        "python-magic",
        "jinja2"
    ],
    scripts=[
        'wsl-windows-toolbar.py'
    ],
    include_package_data=True
)
