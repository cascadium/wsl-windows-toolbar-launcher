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
    version="",
    author="",
    author_email="",
    description="",
    long_description=long_description,
    url="",
    python_requires='>=3',
    install_requires=[
        "click",
        "pyxdg",
        "winshell",
        "swinlnk",
        "pillow",
        "python-magic"
    ],
    scripts=[
        'wsl-windows-toolbar.py'
    ]
)
