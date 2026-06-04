#!/usr/bin/python3
"""Run KiBot 1.9.0 under Python 3.14 (Ubuntu 26.04 "Resolute" and later).

Python 3.14 removed the long-deprecated `ast.Num` / `ast.Str` classes and the
`ast.Constant.s` / `.n` attribute shims (present through 3.12, gone in 3.14).
KiBot 1.9.0's `macros.py` and its bundled `mcpyrate` 3.6.0 still reference them,
and they run at *import time* via the `document` macro -- so plain `kibot`
crashes on startup with errors like:

    AttributeError: 'Constant' object has no attribute 's'
    ... module 'ast' has no attribute 'Num'

before it ever reads a board. This is a distro transition gap (the apt package
was built under 3.13, where it works, then the default flipped to 3.14 and KiBot
wasn't rebuilt/fixed); it has nothing to do with KiCAD 10 or any board file.
KiBot's pcbnew dependency is ABI-locked to the system Python 3.14, so we can't
just run it under an older interpreter -- we patch the missing `ast` names back
in and hand off to the real entry point. No system/apt files are modified.

Usage (from inside a board directory):
    python3 ../tools/kibot314.py -c make_fab.kibot.yaml

Forward-safe: once KiBot/mcpyrate ship a 3.14-compatible release (or you're on a
Python that still has these names), the shims below become no-ops via hasattr().
"""
import os
import sys

# KiBot's pcbnew is built for the system interpreter; make sure we run under it
# regardless of any PATH/mise shims that put another python first.
_SYS_PY = "/usr/bin/python3"
if os.path.realpath(sys.executable) != os.path.realpath(_SYS_PY):
    os.execv(_SYS_PY, [_SYS_PY, os.path.abspath(__file__), *sys.argv[1:]])

import ast

# Restore Constant.s / .n as read/write aliases for .value
# (macros.py both reads `value.s` and writes `help_str.s = ...`).
if not hasattr(ast.Constant, "s"):
    ast.Constant.s = property(lambda self: self.value,
                              lambda self, v: setattr(self, "value", v))
if not hasattr(ast.Constant, "n"):
    ast.Constant.n = property(lambda self: self.value,
                              lambda self, v: setattr(self, "value", v))

# Restore the ast.Num / ast.Str *names*. The modern parser only ever emits
# ast.Constant, so the old `type(x) is ast.Num` checks are dead fallbacks --
# point the names at unique sentinels that never match, so we only prevent the
# AttributeError on name lookup without altering any behavior.
for _name in ("Num", "Str", "Bytes", "NameConstant", "Ellipsis"):
    if not hasattr(ast, _name):
        setattr(ast, _name, type(_name, (), {}))

if __name__ == "__main__":
    import re
    from importlib.metadata import distribution
    eps = distribution("kibot").entry_points
    main = next(e for e in eps
                if e.group == "console_scripts" and e.name == "kibot").load()
    sys.argv[0] = re.sub(r"(-script\.pyw?|\.exe)?$", "", "kibot")
    sys.exit(main())
