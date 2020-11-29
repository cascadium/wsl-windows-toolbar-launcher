import setuptools
import sys
from platform import uname

if sys.version_info.major <= 2:
    sys.stderr.write("Python >=3 required (detected: %s.%s.x)" % (
        sys.version_info.major,
        sys.version_info.minor
    ))
    exit(1)

if uname().system != "Linux" or "microsoft" not in uname().release:
    sys.stderr.write("WSL Linux environment required (detected: %s [%s])" % (
        uname().system,
        uname().release
    ))
    exit(1)

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="wsl-windows-toolbar",
    version="0.6.0",
    author="Frank Quinn",
    author_email="fquinn@cascadium.io",
    description="Adds linux GUI application menu to a windows toolbar",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/cascadium/wsl-windows-toolbar-launcher",
    python_requires='>=3',
    install_requires=[
        "click>=7",
        "pyxdg>=0.26",
        "winshell>=0.6",
        "swinlnk>=0.1.4",
        "pillow>=6",
        "python-magic>=0.4.15",
        "jinja2>=2.11"
    ],
    packages=[
        "wsl_windows_toolbar"
    ],
    package_dir={
        "wsl_windows_toolbar": ""
    },
    package_data={
        'wsl_windows_toolbar': [
            "wsl-windows-toolbar-template.bat.j2",
            "wsl-windows-toolbar-template.sh.j2",
            "__init__.py"
        ]
    },
    entry_points={
        'console_scripts': ['wsl-windows-toolbar=wsl_windows_toolbar.wsl_windows_toolbar:cli'],
    }
)
