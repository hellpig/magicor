#!/usr/bin/env python3
#
# Magicor Level Editor
# Copyright 2006  Peter Gebauer. Licensed as Public Domain.
# (see LICENSE for more info)
from optparse import OptionParser
import sys, os
sys.path.append(".")

##-->win
def change_to_correct_path():
    exe_base_dir = os.path.abspath(os.path.dirname(__file__))
    os.chdir(exe_base_dir)
    if exe_base_dir not in sys.path:
        sys.path.insert(0, exe_base_dir)

change_to_correct_path()
##<--win

from magicor import getConfig

try:
    from magicor.editor.gtkgui import GtkEditor
except ImportError as exc:
    raise SystemExit(
        "The game itself is ported to Python 3, but the optional level editor "
        "still requires the obsolete PyGTK 2 stack and is not supported by "
        "this port. Original import error: %s" % exc
    )

parser = OptionParser()
parser.add_option("-c", "--config", dest="configPath",
                  default=("." if sys.platform == "win32" else "~/.magicor"),
                  help="directory containing magicor-editor.conf")
baseConf = os.path.join(os.path.dirname(__file__), "etc",
                        "magicor-editor.conf")

(options, args) = parser.parse_args()

user_conf = os.path.expanduser(os.path.expandvars(options.configPath))
if os.path.isdir(user_conf) or not os.path.splitext(user_conf)[1]:
    user_conf = os.path.join(user_conf, "magicor-editor.conf")
conf = getConfig([baseConf, user_conf])
conf["data_path"] = "data"
if sys.platform == "win32":
    conf["user_path"] = "."
GtkEditor(conf, args and args[0] or None)
