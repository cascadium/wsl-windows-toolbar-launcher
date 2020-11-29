import pylnk3
from datetime import datetime
import os

CONST_EXTENSION_SEPARATOR = '.'
CONST_DIR_SEPARATOR = "\\"
CONST_SHORTCUT_SPOOF_SIZE = 170496


def path_levels(p):
    components = p.split(CONST_DIR_SEPARATOR)
    dirname = CONST_DIR_SEPARATOR.join(components[0:-1])
    # In last split, trailing separator is expected
    if len(components) <= 2:
        dirname = dirname + CONST_DIR_SEPARATOR
    base = components[-1]
    if base != '':
        for level in path_levels(dirname):
            yield level
    yield p


def path_segment_create_for_file(path):
    entry = pylnk3.PathSegmentEntry()
    entry.type = pylnk3.TYPE_FILE
    entry.file_size = CONST_SHORTCUT_SPOOF_SIZE
    entry.full_name = path.split(CONST_DIR_SEPARATOR)[-1]
    return entry


def path_segment_create_for_folder(path):
    entry = pylnk3.PathSegmentEntry()
    entry.type = pylnk3.TYPE_FOLDER
    entry.full_name = path.split(CONST_DIR_SEPARATOR)[-1]
    return entry


def create_shortcut_pylink3(executable, link_file=None, arguments=None, comment=None, icon_file=None, icon_index=0, work_dir="%USERPROFILE%"):
    lnk = pylnk3.create(link_file)
    lnk.link_flags._flags['IsUnicode'] = True
    lnk.link_info = None
    levels = list(path_levels(executable))
    print(levels)
    elements = [pylnk3.RootEntry(pylnk3.ROOT_MY_COMPUTER),
                pylnk3.DriveEntry(levels[0])]

    for level in levels[1:-1]:
        elements.append(path_segment_create_for_folder(level))
    elements.append(path_segment_create_for_file(levels[-1]))

    lnk.shell_item_id_list = pylnk3.LinkTargetIDList()
    lnk.shell_item_id_list.items = elements
    # lnk.link_flags._flags['HasLinkInfo'] = True
    if arguments:
        lnk.link_flags._flags['HasArguments'] = True
        lnk.arguments = arguments
    if comment:
        lnk.link_flags._flags['HasName'] = True
        lnk.description = comment
    if icon_file:
        lnk.link_flags._flags['HasIconLocation'] = True
        lnk.icon = icon_file
    lnk.icon_index = icon_index
    if work_dir:
        lnk.link_flags._flags['HasWorkingDir'] = True
        lnk.work_dir = work_dir
    if link_file:
        lnk.save()
    return lnk


def create_shortcut_powershell(link_file, executable, arguments="", comment="", icon_file="", work_dir="%USERPROFILE%"):
    powershell_cmd = "powershell.exe -ExecutionPolicy Bypass -NoLogo -NonInteractive -NoProfile "
    powershell_cmd += "-Command '"
    powershell_cmd += '$ws = New-Object -ComObject WScript.Shell; '
    powershell_cmd += '$s = $ws.CreateShortcut("%s");' % link_file
    powershell_cmd += '$s.TargetPath = "%s";' % executable
    powershell_cmd += '$s.Arguments = "%s";' % arguments.replace('"', '`"')
    powershell_cmd += '$s.Description = "%s";' % comment
    powershell_cmd += '$s.WorkingDirectory = "%s";' % work_dir
    powershell_cmd += '$s.IconLocation = "%s";' % icon_file
    powershell_cmd += '$s.Save()'
    powershell_cmd += "'"
    os.popen(powershell_cmd).read().rstrip()
    return link_file


create_shortcut = create_shortcut_pylink3