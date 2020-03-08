# WSL Windows Toolbar Launcher

This script will create a Windows toolbar launcher for an underlying WSL install which
can be used to fire up linux native applications directly from Windows via the standard
Windows toolbar, like this:

![Alt Text](assets/demo.gif)

It's particularly cool because WSL 2 is coming which is unlocking unprecedented performance
and compatibility improvements, so this will literally bring the full suite of Linux GUI
applications directly to Windows UI.

## Prerequisites

The script expects to be run **within** the WSL execution environment with:

* A complete WSL install ready with bash and python3 installed.
* An **X11 Server** running on your **windows host** (e.g. X410, Xming etc). This server
  must be *reachable* from your WSL env (test with something like `wsl.exe -- source ~/.bashrc ; xterm"`).
  If this fails, check your `DISPLAY` variable (more details in [troubleshooting](#troubleshooting)).
* A desktop environment which has a freedesktop menu installed (e.g. gnome / xfce).

## Installing and Running

To install:

    python3 -m pip install git+https://github.com/cascadium/wsl-windows-toolbar-launcher#egg=wsl-windows-toolbar

To run:

    wsl-windows-toolbar.py

After installation, right click on your toolbar, go to
`Toolbars -> New toolbar...` and select
`%USERPROFILE%\.config\wsl-windows-toolbar-launcher\menus\WSL` as the target folder (unless
you selected an alternative directory).

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

## Troubleshooting

### No applications launching

If no applications are launching at all, it's most likely an issue with either:

* `DISPLAY` not being set correctly
* `DISPLAY` being set fine, but its destination is not accessible from the WSL environment
* The X11 server isn't set up to allow access from external hosts (how to configure this will depend on your X11 server
  so please refer to their documentation)

Note that for this section, you can check which version of WSL you're using with:

    wsl.exe -l --verbose

#### Check WSL1 `$DISPLAY` variable

If you're running WSL1, the `DISPLAY` variable for WSL1 should simply be `localhost:0.0`
if this is the default distribution.

#### Check WSL2 `$DISPLAY` variable

Unfortunately for WSL2, it's a little more complicated for now, though I think they're
planning on fixing this. You'll need something like this to extract the correct host:

    export DISPLAY=$(grep -m 1 nameserver /etc/resolv.conf | awk '{print $2}'):0.0

However, in addition to this, you also need to disable the windows firewall for the WSL network.
And to make things worse, it doesn't persist on reboot (must be run as admin):

    powershell.exe -Command "Set-NetFirewallProfile -DisabledInterfaceAliases \"vEthernet (WSL)\""

If anyone has an alternative way to make
this work automatically, I'd love to hear it, because WSL2 is amazing (though still in preview),
but this functionality is annoying. Not just for this, but for accessing any windows native TCP
services from WSL (e.g. database).

### Application X not working

Does the application use dbus? If so, it's recommended to put something like this in your `.bashrc` to satisfy the many
applications which depend on dbus to function:

    dbus_status=$(service dbus status)
    if [[ $dbus_status = *"is not running"* ]]; then
      sudo service dbus --full-restart
    fi

Also check that the `.bashrc` tweaks are added **before any nastiness** like this in your `.bashrc` which would prevent `DISPLAY` from being set:

    # If not running interactively, don't do anything
    [ -z "$PS1" ] && return

You can do similar with `docker` or any other service which you will need access to, but won't necessarily already be
running in a vanilla WSL installation.

To debug further, you can run the shortcut directly from the command line from a `cmd` shell:

    wsl.exe -d <your-wsl-distro> -u <your-wsl-user> -- source ~/.bashrc ; env; xterm

Replacing xterm with whatever command you're trying to launch. Note the `env` command will
print out all environment variables set before running `xterm` in this example, so this should
help you double check if `DISPLAY` is really set correctly. 


## Raising Issues

Issues may be raised in github issues. Before raising an issue though:

* Verify that you have an X Server running on windows 10. Popular options include X410 or Xming.
* Verify that you can actually launch X applications from a WSL terminal (e.g. try running xterm).

If an issue is to be required, please prepare the log output from the command and details on your
execution environment. Ideally try and find the `.desktop` file relating to the failing software as well.
