#!/usr/bin/env python3

import os
import logging
import shutil
import subprocess
import sys
import magic
from platform import uname
import click
from PIL import Image
# Set up default logging format and level
import xdg.Menu
import xdg.IconTheme
from click._compat import raw_input
from jinja2 import Environment, PackageLoader, FileSystemLoader


logging.basicConfig(level=logging.INFO, format='%(asctime)s[%(levelname)s]: %(message)s')
logger = logging.getLogger(__name__)

# Pre-run checks up here
if uname().system != "Linux" or "microsoft" not in uname().release:
    logger.error("WSL Linux environment required (detected: %s [%s])" %
                 uname().system,
                 uname().release
                 )
    exit(1)

# Check required tools are available
for exe in ["cmd.exe", "attrib.exe", "powershell.exe", "wscript.exe", "wslpath"]:
    # Just check for non zero return codes
    logger.debug("Checking availability of %s...", exe)
    try:
        proc = subprocess.check_output(["which", exe])
        logger.debug("Found: %s", proc.rstrip().decode())
    except subprocess.CalledProcessError:
        logger.error("The %s application must be in the current user's executable $PATH.", exe)
        sys.exit(os.EX_UNAVAILABLE)

PROC_MOUNTS = "/proc/mounts"
DEFAULT_HOST_MOUNTPOINT = "/mnt/c"
if os.path.exists(PROC_MOUNTS):
    with open(PROC_MOUNTS) as mount_fh:
        for mount in mount_fh.readlines():
            fs, mp, typ, opts, dump, pas = mount.rstrip().split()
            if typ in ["drvfs", "9p"]:
                DEFAULT_HOST_MOUNTPOINT = mp

WINDOWS_USERPROFILE = subprocess.check_output(
    ["cmd.exe", "/C", "echo", "%USERPROFILE%"],
    stderr=subprocess.DEVNULL
).rstrip().decode("utf-8")
WSL_USERPROFILE = subprocess.check_output(
    ["wslpath", WINDOWS_USERPROFILE]
).rstrip().decode("utf-8")

DEFAULT_INSTALL_DIRECTORY = os.path.join(
    WSL_USERPROFILE, ".config", "wsl-windows-toolbar-launcher/menus")
DEFAULT_METADATA_DIRECTORY = os.path.join(
    WSL_USERPROFILE, ".config", "wsl-windows-toolbar-launcher/metadata")

FREEDESKTOP_FIELD_CODES = [
    "%f",
    "%F",
    "%u",
    "%U",
    "%d",
    "%D",
    "%n",
    "%N",
    "%i",
    "%c",
    "%k",
    "%v",
    "%m"
]

# Default environment detection for optional extras
has_cairosvg = False
has_imagemagick = False

try:
    from cairosvg import svg2png
    has_cairosvg = True
except ImportError:
    logger.warning("Could not find cairosvg - will not be able to convert svg ")
    pass

try:
    if 'ImageMagick' in subprocess.check_output(["convert", "-version"]).rstrip().decode():
        has_imagemagick = True
except Exception:
    logger.warning("Could not find imagemagick - some xpm icons may not convert correctly")
    pass


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
@click.option("--preferred-theme",
              "-t",
              type=str,
              default="Adwaita",
              show_default=True,
              help="Preferred menu theme to use")
@click.option("--alternative-theme",
              "-T",
              type=str,
              default=[
                  "Papirus",
                  "Humanity",
                  "elementary-xfce"
              ],
              show_default=True,
              multiple=True,
              help="Alternative menu themes to consider (pass multiple times)")
@click.option("--jinja-template-batch",
              "-j",
              type=click.File('r'),
              default=None,
              show_default=False,
              help="Optional Jinja template to use instead of the inbuilt default (advanced users only)")
@click.option("--jinja-template-shell",
              "-J",
              type=click.File('r'),
              default=None,
              show_default=False,
              help="Optional Jinja template to use instead of the inbuilt default (advanced users only)")
@click.option("--rc-file",
              "-r",
              type=click.File('r'),
              default=os.path.expanduser("~/.bashrc"),
              show_default=False,
              help="Optional rc file to source prior to launching the command instead of ~/.bashrc")
@click.option("--launch-directory",
              "-D",
              type=click.Path(exists=True, file_okay=False),
              default=os.path.expanduser("~"),
              show_default=False,
              help="Optional default linux path to open applications relative to (defaults to ~)")
@click.option("--batch-encoding",
              "-E",
              type=str,
              default=None,
              show_default=False,
              help="Optional batch file output encoding (defaults to None)")
@click.option("--use-batch-newline-crlf",
              "-N",
              is_flag=True,
              default=False,
              show_default=False,
              help="Optional use batch file newline value CRLF (defaults to False)")
def cli(install_directory,
        metadata_directory,
        distribution,
        user,
        confirm_yes,
        menu_file,
        wsl_executable,
        target_name,
        preferred_theme,
        alternative_theme,
        jinja_template_batch,
        jinja_template_shell,
        rc_file,
        launch_directory,
        batch_encoding,
        use_batch_newline_crlf):

    # Debug information
    logger.info("distribution = %s", distribution)
    logger.info("user = %s", user)
    logger.info("confirm_yes = %s", confirm_yes)
    logger.info("menu_file = %s", menu_file.name)
    logger.info("wsl_executable = %s", wsl_executable)
    logger.info("target_name = %s", target_name)
    logger.info("preferred_theme = %s", preferred_theme)
    logger.info("alternative_theme = %s", alternative_theme)
    logger.info("jinja_template_batch = %s", jinja_template_batch.name if jinja_template_batch else None)
    logger.info("jinja_template_shell = %s", jinja_template_shell.name if jinja_template_shell else None)
    logger.info("rc_file = %s", rc_file.name)
    logger.info("has_imagemagick = %s", has_imagemagick)
    logger.info("has_cairosvg = %s", has_cairosvg)
    logger.info("launch_directory = %s", launch_directory)
    logger.info("batch_encoding = %s", batch_encoding)
    logger.info("use_batch_newline_crlf = %s", use_batch_newline_crlf)

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

    # Make metadata a hidden system file to hide it from indexer (cleaner search results for powertoys etc)
    set_hidden_from_indexer(metadata_directory)

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
                lsf.write('CreateObject("Wscript.Shell").Run """" & WScript.Arguments(0) & """", 0, False')
        except Exception:
            logger.error("Could not create %s", silent_launcher_script_file)
            sys.exit(os.EX_IOERR)

    # Build windows path for the launcher script
    silent_launcher_script_file_win = get_windows_path_from_wsl_path(silent_launcher_script_file)

    # Load in the template which is used to generate the launcher script
    if not jinja_template_batch:
        # Default load from package
        env = Environment(loader=PackageLoader('wsl_windows_toolbar', package_path=''))
        batch_template = env.get_template("wsl-windows-toolbar-template.bat.j2")
        shell_template = env.get_template("wsl-windows-toolbar-template.sh.j2")
    else:
        # Optionally load from custom filesystem location
        env = Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(jinja_template_batch.name))))
        batch_template = env.get_template(os.path.basename(jinja_template_batch.name))
        shell_template = env.get_template(os.path.basename(jinja_template_shell.name))

    # Create shortcut files
    shortcuts_installed = 0
    for path, entry in entries.items():
        logger.info("Creating menu item for: %s", path)
        exec_cmd = entry.getExec()
        # https://specifications.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html#key-path
        exec_dir = entry.getPath()
        # https://specifications.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html#key-terminal
        run_in_terminal = entry.getTerminal()

        if not exec_dir:
            exec_dir = launch_directory

        # These parts aren't relevant for menu launcher so prune out from the command
        for substr in FREEDESKTOP_FIELD_CODES:
            exec_cmd = exec_cmd.replace(substr, "")

        # Carve the way for the shortcut
        shortcut_path = os.path.join(install_directory, "%s.lnk" % path)
        os.makedirs(os.path.dirname(shortcut_path), exist_ok=True)
        logger.debug("Will create shortcut file: %s", shortcut_path)

        # Normalize the icon to a windows path so shortcut can find it
        icon = entry.getIcon()
        metadata_prefix = os.path.join(metadata_directory, "%s" % path)
        ico_file_winpath = create_windows_icon(
            icon if icon else entry.getName().lower(),
            metadata_prefix,
            preferred_theme=preferred_theme,
            alternative_theme=alternative_theme
        )

        shell_launcher_path = os.path.join(metadata_directory, "%s.sh" % path)
        template_dict = {
            "distribution": distribution,
            "user": user,
            "command": exec_cmd,
            "wsl": wsl_executable,
            "rcfile": rc_file.name,
            "launch_script": shell_launcher_path,
            "exec_dir": exec_dir,
            "run_in_terminal": run_in_terminal
        }

        # Create a little shell launcher for the executable
        with open(shell_launcher_path, mode="w") as script_handle:
            script_handle.write(shell_template.render(template_dict))
        # Make executable
        os.chmod(shell_launcher_path, 509)
        set_hidden_from_indexer(shell_launcher_path)

        # Create a little batch file launcher for the executable
        batch_launcher_path = os.path.join(metadata_directory, "%s.bat" % path)
        batch_newline = "\r\n" if use_batch_newline_crlf else None
        with open(batch_launcher_path, mode="w", encoding=batch_encoding, newline=batch_newline) as script_handle:
            script_handle.write(batch_template.render(template_dict))
        batch_launcher_path_win = get_windows_path_from_wsl_path(batch_launcher_path)

        if run_in_terminal:
            windows_lnk = create_shortcut(
                shortcut_path,
                batch_launcher_path_win,
                comment=entry.getComment(),
                icon_file=ico_file_winpath
            )
        else:
            windows_lnk = create_shortcut(
                shortcut_path,
                "wscript",
                '"%s" "%s"' % (silent_launcher_script_file_win, batch_launcher_path_win),
                comment=entry.getComment(),
                icon_file=ico_file_winpath
            )
        set_hidden_from_indexer(batch_launcher_path)
        logger.debug("Created %s", windows_lnk)
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


def create_shortcut(link_file, executable, arguments="", comment="", icon_file=""):
    windows_lnk = get_windows_path_from_wsl_path(link_file)
    powershell_cmd = "powershell.exe -ExecutionPolicy Bypass -NoLogo -NonInteractive -NoProfile "
    powershell_cmd += "-Command '"
    powershell_cmd += '$ws = New-Object -ComObject WScript.Shell; '
    powershell_cmd += '$s = $ws.CreateShortcut("%s");' % windows_lnk
    powershell_cmd += '$s.TargetPath = "%s";' % executable
    powershell_cmd += '$s.Arguments = "%s";' % arguments.replace('"', '`"')
    powershell_cmd += '$s.Description = "%s";' % comment
    powershell_cmd += '$s.WorkingDirectory = "%USERPROFILE%";'
    powershell_cmd += '$s.IconLocation = "%s";' % icon_file
    powershell_cmd += '$s.Save()'
    powershell_cmd += "'"
    logger.debug("Powershell command to create shortcut: %s", powershell_cmd)
    os.popen(powershell_cmd).read().rstrip()
    return windows_lnk


def set_hidden_from_indexer(path):
    try:
        subprocess.check_output(["attrib.exe", "+I", "+S", "+H", get_windows_path_from_wsl_path(path)])
        logger.debug("Set hidden system attributes in metadata directory %s", path)
    except subprocess.CalledProcessError:
        logger.exception("Failed to set hidden system attributes in metadata directory %s", path)


def create_windows_icon(icon,
                        metadata_prefix,
                        preferred_theme=None,
                        alternative_theme=None):
    logger.debug("Creating icon files for: %s, %s [%s]", icon, metadata_prefix, preferred_theme)
    os.makedirs(os.path.dirname(metadata_prefix), exist_ok=True)
    icon_path = xdg.IconTheme.getIconPath(icon, theme=preferred_theme)
    if not icon_path:
        for icon_c in [icon, icon.lower()]:
            if alternative_theme:
                for theme in alternative_theme:
                    logger.debug("Checking with theme: %s", theme)
                    icon_path = xdg.IconTheme.getIconPath(icon_c, theme=theme)
                    if icon_path:
                        icon = icon_c
                        logger.debug("Found icon path: %s for theme %s", icon_c, theme)
                        break

    if icon_path:
        filename, extension = os.path.splitext(icon_path)
        png_file = metadata_prefix + ".png"
        mime_type = magic.from_file(icon_path, mime=True)

        try:
            # Some icons appear to have the wrong extension on windows, so check mime type here too
            if extension == ".png" or mime_type == "image/png":
                shutil.copyfile(icon_path, png_file)
            elif has_cairosvg and (extension == ".svg" or mime_type == "image/svg"):
                # Attempt with svg2png if available
                with open(icon_path, 'rb') as f:
                    svg2png(file_obj=f, write_to=png_file)
            else:
                # Attempt with PIL if available
                img = Image.open(icon_path)
                img.save(png_file)
        except Exception as e:
            if has_imagemagick:
                logger.debug("Could not convert using python methods - falling back on imagemagick")
                try:
                    subprocess.check_output(["convert", icon_path, png_file], timeout=10)
                    logger.debug("Converted %s to %s using imagemagick", icon_path, png_file)
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    logger.exception("Failed to create or find png file for %s - icon will not be available (%s: %s)",
                                     icon_path, type(e).__name__, e)
                    png_file = None

        if png_file:
            try:
                # Should have a png file available here now - convert to icon
                img = Image.open(png_file)
                ico_file = metadata_prefix + ".ico"
                img.save(ico_file)
                logger.debug("Successfully created %s", ico_file)
                # Mark both icon and png as system
                set_hidden_from_indexer(png_file)
                set_hidden_from_indexer(ico_file)
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
