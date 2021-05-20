#!/usr/bin/python

import fmf
from pathlib import Path
import subprocess

tree_root = Path.cwd().absolute()
node = fmf.Tree(tree_root).find("/plans")
with node as data:
    data["discover"]["url"] = "https://github.com/packit/packit.git"
    data["discover"]["ref"] = (
        subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    )
