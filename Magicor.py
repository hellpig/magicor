#!/usr/bin/env python3
#
# Magicor
# Copyright 2006  Peter Gebauer. Licensed as Public Domain.
# (see LICENSE for more info)
import sys, os

def change_to_correct_path():
    """Run relative to the source folder on every operating system."""
    exe_base_dir = os.path.abspath(os.path.dirname(__file__))
    os.chdir(exe_base_dir)
    if exe_base_dir not in sys.path:
        sys.path.insert(0, exe_base_dir)

change_to_correct_path()

from optparse import OptionParser
sys.path.append(".")
from magicor import GameEngine, getConfig, parse_printkeys
from magicor.states.intro import CopyrightNoticeState

parser = OptionParser(usage="%prog [options]")

parser.add_option("-c", "--config", dest="configPath",
                  default=("." if sys.platform == "win32" else "~/.magicor"),
                  help="directory containing magicor.conf")
baseConf = os.path.join(os.path.dirname(__file__), "etc", "magicor.conf")

parser.add_option("-j", "--joystick",
                  action="store", type="int", dest="joystick",
                  default=None,
                  help="enable/disable joystick")
parser.add_option("-m", "--music",
                  action="store", type="int", dest="music",
                  default=None,
                  help="enable/disable music")
parser.add_option("-s", "--sound",
                  action="store", type="int",  dest="sound",
                  default=None,
                  help="enable/disable sound")
parser.add_option("-f", "--fullscreen",
                  action="store", type="int",  dest="fullscreen",
                  default=None,
                  help="enable/disable fullscreen")
parser.add_option("-d","--dev", type="int", dest= "devmode",
                  default=None, help="enable dev keys")
parser.add_option("-k","--keysprintdbg",type="string", dest="printkeys",default="",help="keys to enable selective printing of debug info. Separator is ':'")
(options, args) = parser.parse_args()

user_conf = os.path.expanduser(os.path.expandvars(options.configPath))
if os.path.isdir(user_conf) or not os.path.splitext(user_conf)[1]:
    user_conf = os.path.join(user_conf, "magicor.conf")
paths = [baseConf, user_conf]
conf = getConfig(paths)

# The source distribution expects the separate data archive to be extracted
# as a data folder beside Magicor.py.
conf["data_path"] = "data"
if sys.platform == "win32":
    conf["user_path"] = "."

if options.joystick != None:
    conf["joystick"] = bool(options.joystick)
if options.music != None:
    conf["music"] = options.music
if options.sound != None:
    conf["sound"] = options.sound
if options.fullscreen != None:
    conf["fullscreen"] = bool(options.fullscreen)
if options.devmode != None:
    conf["devmode"] = bool(options.devmode)
parse_printkeys(options.printkeys)
gameEngine = GameEngine(conf)
gameEngine.start(CopyrightNoticeState(conf, None, gameEngine.screen))
