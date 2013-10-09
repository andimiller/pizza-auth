#!/usr/bin/env python 
"""
Auth shell
"""
import sys
from keytools import KeyTools
from ldaptools import LDAPTools
from reddittools import RedditTools
import json
from blessings import Terminal

term = Terminal()
# Load config
fh=open("config.json", "r")
config = json.loads(fh.read())
fh.close()
# Set up tools
keytools = KeyTools(config)
ldaptools = LDAPTools(config)
reddittools = RedditTools(config, ldaptools)
# Enter prompt
print("Entering interactive PIZZA-Auth admin shell")
sys.ps1 = "{t.magenta}pizza-auth > {t.normal}".format(t=term)
import code
code.InteractiveConsole(locals=globals()).interact()
