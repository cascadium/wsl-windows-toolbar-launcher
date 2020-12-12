# WSL Windows Toolbar Launcher

This script will create a Windows toolbar launcher for an underlying WSL install which
can be used to fire up linux native applications directly from Windows via the standard
Windows toolbar, like this:

![Demo](https://github.com/cascadium/wsl-windows-toolbar-launcher/raw/master/assets/demo.gif)

It's particularly cool because WSL 2 is coming which is unlocking unprecedented performance
and compatibility improvements, so this will literally bring the full suite of Linux GUI
applications directly to Windows UI.

## Prerequisites

The script expects to be run **within** the WSL execution environment with:

* A complete WSL install ready with bash and python3 installed.
* An **X11 Server** running on your **windows host** (e.g. X410, Xming etc). This server
  must be *reachable* from your WSL env (test with something like `wsl.exe -- source ~/.bashrc ; xterm"`).
  If this fails, check your `DISPLAY` variable (more details in [troubleshooting](#troubleshooting)).
* A freedesktop menu installed (e.g. gnome-menus or a full desktop environment).

And optionally (but recommended):

* An installation of cairosvg if works on your distro (`pip install cairosvg`). This will allow you to convert `.svg`
  based icons.
* Imagemagick installed (`sudo apt install imagemagick` / `dnf install imagemagick` etc). This will allow you to have
  an additional opportunity to convert appropriate icon files if other methods fail.

## Installing and Running

To install:

    pip install wsl-windows-toolbar

To run:

    wsl-windows-toolbar

After installation, right click on your toolbar, go to
`Toolbars -> New toolbar...` and select
`%USERPROFILE%\.config\wsl-windows-toolbar-launcher\menus\WSL` as the target folder (unless
you selected an alternative directory).

Note there are many options available with `--help` if you'd prefer to use alternative locations.

## Updating

If new software has been installed in the WSL environment, simply run the script again from the WSL environment to pick
the new GUIs up.

Notable changes:

* Change in 0.3: Command is now `wsl-windows-toolbar` without the trailing `.py`.

## Advanced Usage / Options

```
$ python wsl-windows-toolbar.py  --help
Usage: wsl_windows_toolbar.py [OPTIONS]

Options:
  -i, --install-directory PATH    Install the launchers here [default:
                                  /c/Users/$USER/.config/wsl-windows-toolbar-
                                  launcher/metadata]
  -m, --metadata-directory PATH   Install any metadata here [default:
                                  /c/Users/$USER/.config/wsl-windows-toolbar-
                                  launcher/metadata]
  -d, --distribution TEXT         WSL Distro to generate shortcuts for
                                  [default: $WSL_DISTRO_NAME]
  -u, --user TEXT                 WSL Distro's user to launch programs as
                                  [default: $USER]
  -y, --confirm-yes               Assume the answer to all confirmation
                                  prompts is 'yes'  [default: False]
  -f, --menu-file FILENAME        The *.menu menu file to parse  [default:
                                  /etc/xdg/menus/gnome-applications.menu]
  -w, --wsl-executable TEXT       Path to the WSL executable relative to the
                                  windows installation  [default:
                                  C:\Windows\System32\wsl.exe]
  -n, --target-name TEXT          Name to give to the created installation
                                  (will be displayed in toolbar menu)
                                  [default: WSL]
  -t, --preferred-theme TEXT      Preferred menu theme to use  [default:
                                  Adwaita]
  -T, --alternative-theme TEXT    Alternative menu themes to consider (pass
                                  multiple times)  [default: Papirus,
                                  Humanity, elementary-xfce]
  -j, --jinja-template-batch FILENAME
                                  Optional Jinja template to use instead of
                                  the inbuilt default (advanced users only)
  -J, --jinja-template-shell FILENAME
                                  Optional Jinja template to use instead of
                                  the inbuilt default (advanced users only)
  -r, --rc-file FILENAME          Optional rc file to source prior to
                                  launching the command instead of ~/.bashrc
  -D, --launch-directory DIRECTORY
                                  Optional default linux path to open
                                  applications relative to (defaults to ~)
  --help                          Show this message and exit.
```

### Advanced Launcher Behaviour

The launcher process is fairly broken down to separate responsibilities and allow customizations
at several layers. It looks like this:

    lnk -> vbscript (sometimes) -> bat -> wsl bash -> app

The `.lnk` is the shortcut with the icon etc. The vbscript exists only to launch the batch file
without a terminal window appearing. The batch file bootstraps the wsl bash script using `wsl.exe`
which in turn (finally) launches the app. It may seem convoluted but I have found this is the
easiest way to break it down to allow flexibility and ease of maintenance at each layer.

Note the vbscript is only called if `run_in_terminal` is set to false (as it tends to be for most
applications). The templates which define the batch and bash files are used may be overridden
by `-j` and `-J` respectively, though you shouldn't usually need to override this behaviour.

The default templates used are `wsl-windows-toolbar-template.bat.j2` and
`wsl-windows-toolbar-template.sh.j2`. The following possible variables passed
through from the script:

* `distribution`: The distribution selected in the script
* `user`: The user selected in the script
* `command`: The individual command for each launcher entry in WSL environment (e.g. `xterm`)
* `wsl`: The wsl executable discovered
* `rcfile`: The rc file (e.g. `.bashrc`) to source prior to launch selected in the script
* `launch_script`: The path of the linux launcher script
* `exec_dir`: The directory in which this command will be run (linux path)
* `run_in_terminal`: Boolean specifying whether or not this app expects to run in a terminal

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

### Firewall Rules

Then you need to worry about the firewall. WSL comes up as a public network, but I wouldn't recommend
allowing all public network traffic to access your X server. So instead, you can go ahead and select
defaults when this sort of prompt comes up:

![Security Alert](https://github.com/cascadium/wsl-windows-toolbar-launcher/raw/master/assets/security_alert.png)

Now, irritatingly this will actively add a block rule (rather than simply not add an allow rule) for public networks
which you will need to disable for the next step by going into Windows Defender Firewall -> Inbound Rules and
**disabling this block rule for TCP on the Public Network**.

If you don't do the above step, the Block rule will take precedence over the Allow allow rule and you won't get through.

Now, right click on Inbound Rules and select `New Rule...`, select TCP port 6000 (most likely) and select defaults. This
will open up your public network for this port... which is also not what you want. What you want is to only allow traffic
from the WSL subnet. So refresh the list, scroll to your recently created name, right click and go to properties. Now
under `Scope`, go to **Remote IP address**, Select `These IP addresses` and add in `172.16.0.0/12` to limit the subnets
which can access this port to the WSL subnet. It should look something like this:

![WSL Subnet Firewall Rule](https://github.com/cascadium/wsl-windows-toolbar-launcher/raw/master/assets/firewall_rule_wsl_subnet.png)

Alternatively you *could* just disable the entire firewall for WSL, but that adds a firewall warning that constantly
irritates me:

    powershell.exe -Command "Set-NetFirewallProfile -DisabledInterfaceAliases \"vEthernet (WSL)\""

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
