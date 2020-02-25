# WSL Windows Toolbar Launcher

This script will create a Windows toolbar launcher for an underlying WSL install which
can be used to fire up linux native applications directly from Windows via the standard
Windows toolbar, like this:

![Alt Text](assets/demo.gif)

It's particularly cool because WSL 2 is coming which is unlocking unprecedented performance
and compatibility improvements, so this will literally bring a full on suite of Linux GUI
applications to Windows.

## Prerequisites

The script expects to be run **within** the WSL execution environment with:

* An **X11 Server** running on your **windows host** (e.g. X410, Xming etc)
* A desktop environment which uses a freedesktop menu (e.g. gnome / xfce)
* Any configuration required to set up X11 (i.e. `DISPLAY=windows-host:0.0`)
  is already present in `~/.bashrc` in the target WSL installation. Note this
  does *not* support going through SSH. You'll get much better
  performance through plain old X11 TCP between your two
  **already local and authenticated** hosts.
* `powershell.exe` (yes the windows executable) available in the PATH. We use it to create the shortcuts without any
  third party dependencies.
* `wscript.exe` available in the PATH. We use it to silently launch the UI windows.
* `wslpath` available in the PATH. We use it to figure out which windows path the WSL files translate to.

It's also recommended to put something like this in your `.bashrc` to satisfy the many applications which depend on dbus
to function:

    dbus_status=$(service dbus status)
    if [[ $dbus_status = *"is not running"* ]]; then
      sudo service dbus --full-restart
    fi

You can do similar with `docker` or any other service which you will need access to, but won't necessarily already be
running in a vanilla WSL installation.

## Installing and Running

    pip install git+https://github.com/cascadium/wsl-windows-toolbar-launcher#egg=wsl-windows-toolbar-launcher
    wsl-windows-toolbar.py

After installation, right click on your toolbar, go to `Toolbars -> New toolbar...` and select `%USERPROFILE%\.config\wsl-windows-toolbar-launcher\menus\WSL` as the target folder.

Note there are many options available with `--help` if you'd prefer to use alternative locations.

## Updating

If new software has been installed in the WSL environment, simply run the script again from the WSL environment to pick
the new GUIs up.

## Advanced Usage / Options

```
$ python wsl-windows-toolbar.py  --help
Usage: wsl-windows-toolbar.py [OPTIONS]

Options:
  -i, --install-directory PATH   Install the launcher targets to this
                                 directory (<target> will be suffixed to this
                                 location)
  -m, --metadata-directory PATH  Install the launcher targets to this
                                 directory (<target> will be suffixed to this
                                 location)
  -d, --distribution TEXT        WSL Distro to generate shortcuts for (will
                                 use default distro if this parameter is not
                                 provided)
  -u, --user TEXT                WSL Distro's user to launch programs as (will
                                 use default user if this parameter is not
                                 provided)
  -y, --confirm-yes              Assume the answer to all confirmation prompts
                                 is 'yes'
  -f, --menu-file FILENAME       The *.menu menu file to parse
  -w, --wsl-executable TEXT      Path to the WSL executable relative to the
                                 windows installation
  -n, --target-name TEXT         Name to give to the created installation
                                 (will be displayed in toolbar menu)
  --help                         Show this message and exit.
```

## Reporting Issues

Issues may be raised in github issues. Before raising an issue though:

* Verify that you have an X Server running on windows 10. Popular options include X410 or Xming.
* Verify that you can actually launch X applications from a WSL terminal (e.g. try running xterm).

If an issue is to be required, please prepare the log output from the command and details on your
execution environment. Ideally try and find the `.desktop` file relating to the failing software as well.
