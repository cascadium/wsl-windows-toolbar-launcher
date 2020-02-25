#!/usr/bin/env python

import os
import logging
import shutil
import subprocess
import sys

import click
from enum import Enum, auto
from PIL import Image
from cairosvg import svg2png

# Set up default logging format and level
import xdg.Menu
import xdg.IconTheme
from click._compat import raw_input

DEFAULT_INSTALL_DIRECTORY = os.path.join(
    os.sep, "c", "Users", os.environ['USER'], ".config", "wsl-windows-toolbar-launcher/menus")
DEFAULT_METADATA_DIRECTORY = os.path.join(
    os.sep, "c", "Users", os.environ['USER'], ".config", "wsl-windows-toolbar-launcher/metadata")

logging.basicConfig(level=logging.INFO, format='%(asctime)s[%(levelname)s]: %(message)s')
logger = logging.getLogger(__name__)


@click.command()
@click.option("--install-directory",
              "-i",
              type=click.Path(),
              default=DEFAULT_INSTALL_DIRECTORY,
              show_default=False,
              help="Install the launchers here [default: /c/Users/$USER/.config/wsl-windows-toolbar-launcher/metadata]")
@click.option("--metadata-directory",
              "-m",
              type=click.Path(),
              default=DEFAULT_METADATA_DIRECTORY,
              show_default=False,
              help="Install any metadata here [default: /c/Users/$USER/.config/wsl-windows-toolbar-launcher/metadata]")
@click.option("--distribution",
              "-d",
              type=str,
              default=os.environ['WSL_DISTRO_NAME'],
              show_default=False,
              help="WSL Distro to generate shortcuts for [default: $WSL_DISTRO_NAME]")
@click.option("--user",
              "-u",
              type=str,
              default=os.environ['USER'],
              show_default=False,
              help="WSL Distro's user to launch programs as [default: $USER]")
@click.option("--confirm-yes",
              "-y",
              is_flag=True,
              default=False,
              show_default=True,
              help="Assume the answer to all confirmation prompts is 'yes'")
@click.option("--menu-file",
              "-f",
              type=click.File('r'),
              default="/etc/xdg/menus/gnome-applications.menu",
              show_default=True,
              help="The *.menu menu file to parse")
@click.option("--wsl-executable",
              "-w",
              type=str,
              default="C:\\Windows\\System32\\wsl.exe",
              show_default=True,
              help="Path to the WSL executable relative to the windows installation")
@click.option("--target-name",
              "-n",
              type=str,
              default="WSL",
              show_default=True,
              help="Name to give to the created installation (will be displayed in toolbar menu)")
def cli(install_directory,
        metadata_directory,
        distribution,
        user,
        confirm_yes,
        menu_file,
        wsl_executable,
        target_name):

    # Debug information
    logger.info("distribution = %s", distribution)
    logger.info("user = %s", user)
    logger.info("confirm_yes t= %s", confirm_yes)
    logger.info("menu_file = %s", menu_file.name)
    logger.info("wsl_executable = %s", wsl_executable)
    logger.info("target_name = %s", target_name)

    # Check required tools are available
    for exe in ["powershell.exe", "wscript.exe", "wslpath"]:
        # Just check for non zero return codes
        logger.debug("Checking availability of %s...", exe)
        try:
            proc = subprocess.check_output(["which", exe])
            logger.debug("Found: %s", proc.rstrip().decode())
        except subprocess.CalledProcessError:
            logger.error("The %s application must be in the current user's executable path.", exe)
            sys.exit(os.EX_UNAVAILABLE)

    # Add distro to directory names, since we want to support multiple concurrent distributions
    install_directory = os.path.join(install_directory, target_name)
    metadata_directory = os.path.join(metadata_directory, target_name)

    # OK print it debug information for these now
    logger.info("install_directory = %s", install_directory)
    logger.info("metadata_directory = %s", metadata_directory)

    if not confirm_yes:
        logger.info("For full list of options available, call script again with --help")
        logger.info("This script will write to the above locations if it can, but giving final chance to chicken out.")
        raw_input("Press <enter> to continue or ctrl+c to abort.")

    # OK we're ready to go - ensure we can create / have write access to the installation directory
    try:
        # Create directory and fear not if it already exists
        os.makedirs(install_directory, exist_ok=True)
        os.makedirs(metadata_directory, exist_ok=True)
    except PermissionError:
        logger.error("No permissions to create directories %s or %s - aborting", install_directory, metadata_directory)
        sys.exit(os.EX_NOPERM)

    # Check we have absolute ownership of this directory - if not, chicken out
    if not is_directory_writable(install_directory):
        logger.error("Could not confirm write access to all contents of %s - aborting", install_directory)
        sys.exit(os.EX_NOPERM)

    # Find all desktop menu items, indexed by menu path
    menu = xdg.Menu.parse(menu_file.name)
    entries = get_desktop_entries(menu)

    # Create shortcut launcher script (avoids terminal being displayed while launching)
    silent_launcher_script_file = os.path.join(metadata_directory, "silent-launcher.vbs")
    if not os.path.exists(silent_launcher_script_file):
        try:
            with open(silent_launcher_script_file, "w") as lsf:
                # If this gets more complicated, we could make this a resource, but at one line, this is fine
                lsf.write('CreateObject("Wscript.Shell").Run "" & WScript.Arguments(0) & "", 0, False')
        except Exception:
            logger.error("Could not create %s", silent_launcher_script_file)
            sys.exit(os.EX_IOERR)

    # Build windows path for the launcher script
    silent_launcher_script_file_win = get_windows_path_from_wsl_path(silent_launcher_script_file)

    # Create shortcut files
    shortcuts_installed = 0
    for path, entry in entries.items():
        logger.info("Creating menu item for: %s", path)
        exec = entry.getExec()
        if "exo-open" in exec:
            logger.warning("Cannot add %s [%s] - exo-open doesn't currently work via this launcher method.", path, exec)
            continue

        # These parts aren't relevant for menu launcher so prune out from the command
        to_strip = ["%u", "%U", "%F"]
        for substr in to_strip:
            exec = exec.replace(substr, "")

        # Carve the way for the shortcut
        shortcut_path = os.path.join(install_directory, "%s.lnk" % path)
        os.makedirs(os.path.dirname(shortcut_path), exist_ok=True)
        logger.debug("Will create shortcut file: %s", shortcut_path)

        # Normalize the icon to a windows path so shortcut can find it
        icon = entry.getIcon()
        metadata_prefix = os.path.join(metadata_directory, "%s" % path)
        if icon:
            ico_file_winpath = create_windows_icon(icon, metadata_prefix)
        else:
            logger.warning("Failed to find icon for %s", path)
            ico_file_winpath = None

        arguments = "-d %s -u %s -- source ~/.bashrc ; %s" % (distribution, user, exec)
        windows_lnk = create_shortcut(
            shortcut_path,
            "wscript",
            '%s "%s %s"' % (silent_launcher_script_file_win, wsl_executable, arguments.replace('"', "'")),
            entry.getComment(),
            ico_file_winpath
        )
        logger.info("Created %s", windows_lnk)
        shortcuts_installed += 1

    logger.info("Finished creating %d shortcuts!", shortcuts_installed)
    logger.info("Before raising an issue, make sure you have Xming / X410 etc set up in your .bashrc.")
    logger.info(
        "Right click on the toolbar, then select Toolbars -> New toolbar... and select the directory '%s'.",
        install_directory
    )


def get_windows_path_from_wsl_path(path):
    return "%s\\%s" % (
        subprocess.check_output(["wslpath", "-w", "-a", os.path.dirname(path)]).rstrip().decode(),
        os.path.basename(path)
    )


def create_shortcut(link_file, executable, arguments=None, comment=None, icon_file=None):
    windows_lnk = get_windows_path_from_wsl_path(link_file)
    powershell_cmd = "powershell.exe -ExecutionPolicy Bypass -NoLogo -NonInteractive -NoProfile "
    powershell_cmd += "-Command '"
    powershell_cmd += '$ws = New-Object -ComObject WScript.Shell; '
    powershell_cmd += '$s = $ws.CreateShortcut("%s");' % windows_lnk
    powershell_cmd += '$s.TargetPath = "%s";' % executable
    powershell_cmd += '$s.Arguments = "%s";' % arguments.replace('"', '`"')
    powershell_cmd += '$s.Description = "%s";' % comment
    powershell_cmd += '$s.IconLocation = "%s";' % icon_file
    powershell_cmd += '$s.Save()'
    powershell_cmd += "'"
    logger.debug("Powershell command to create shortcut: %s", powershell_cmd)
    os.popen(powershell_cmd).read().rstrip()
    return windows_lnk


def create_windows_icon(icon, metadata_prefix):
    logger.debug("Creating icon files for: %s*", metadata_prefix)
    os.makedirs(os.path.dirname(metadata_prefix), exist_ok=True)
    icon_path = xdg.IconTheme.getIconPath(icon, theme="Adwaita")
    if icon_path:
        filename, extension = os.path.splitext(icon_path)
        png_file = metadata_prefix + ".png"

        try:
            if extension == ".png":
                shutil.copy(icon_path, png_file)
            elif extension == ".svg":
                with open(icon_path, 'rb') as f:
                    svg2png(file_obj=f, write_to=png_file)
            else:
                img = Image.open(icon_path)
                img.save(png_file)
        except Exception:
            logger.warning("Failed to create or find png file for %s - icon will not be available", icon_path)
            png_file = None

        if png_file:
            try:
                # Should have a png file available here now - convert to icon
                img = Image.open(png_file)
                ico_file = metadata_prefix + ".ico"
                img.save(ico_file)
                logger.debug("Successfully created %s", ico_file)
                return get_windows_path_from_wsl_path(ico_file)
            except Exception:
                logger.warning("Could not generate icon for %s", png_file)
    else:
        logger.warning("Failed to find icon file for %s", icon)

    return None


def get_desktop_entries(menu, entries=None):
    if entries is None:
        entries = {}
    for entry in menu.getEntries():
        if isinstance(entry, xdg.Menu.Menu):
            # Recurse subdirectory
            get_desktop_entries(entry, entries)
        elif isinstance(entry, xdg.Menu.MenuEntry):
            # We are only interested in "Application" entries
            if entry.DesktopEntry.getType() == "Application":
                # Index desktop entry by path
                if menu.getPath():
                    prefix = menu.getPath() + os.sep
                else:
                    prefix = ""
                entries[prefix + entry.DesktopEntry.getName()] = entry.DesktopEntry

    return entries


def is_directory_writable(base_path):
    writable = True
    # Check the directory is writable
    if os.access(base_path, os.W_OK):
        logger.debug("Can write to %s", base_path)
    else:
        writable = False
        logger.error("Cannot write to %s", base_path)

    for root, dirs, files in os.walk(base_path):
        for path in dirs + files:
            if os.access(base_path, os.W_OK):
                logger.debug("Can write to %s", os.path.join(root, path))
            else:
                writable = False
                logger.error("Cannot write to %s", os.path.join(root, path))

    return writable


if __name__ == '__main__':
    cli()
