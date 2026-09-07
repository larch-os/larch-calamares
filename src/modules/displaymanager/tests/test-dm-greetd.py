#   SPDX-FileCopyrightText: no
#   SPDX-License-Identifier: CC0-1.0
#
# Calamares Boilerplate
import libcalamares
libcalamares.globalstorage = libcalamares.GlobalStorage(None)
libcalamares.globalstorage.insert("testing", True)

# Module prep-work
from src.modules.displaymanager import main
default_desktop_environment = main.DesktopEnvironment("startplasma-x11", "kde-plasma.desktop")

import os
os.makedirs("/tmp/etc/greetd/", exist_ok=True)
try:
    os.remove("/tmp/etc/greetd/config.toml")
except FileNotFoundError as e:
    pass

try:
    import toml
except ImportError:
    # This is a failure of the test-environment.
    import sys
    print("Can't find module toml.", file=sys.stderr)
    sys.exit(0)

# Specific DM test
d = main.DMgreetd("/tmp")
d.set_autologin("d", True, default_desktop_environment)
# .. and again (this time checks load/save)
d.set_autologin("d", True, default_desktop_environment)
d.set_autologin("d", True, default_desktop_environment)

# Larch: with no greeter binaries present, set_autologin() should have
# fallen through to the agreety default.
with open("/tmp/etc/greetd/config.toml") as f:
    written = toml.load(f)
assert "agreety" in written["default_session"]["command"]

# Larch: regreet + cage present -> the regreet branch should be picked,
# not gtkgreet/tuigreet/ddlm/agreety.
os.makedirs("/tmp/usr/bin", exist_ok=True)
for binary in ("regreet", "cage"):
    open(os.path.join("/tmp/usr/bin", binary), "a").close()

d.set_autologin("d", True, default_desktop_environment)
with open("/tmp/etc/greetd/config.toml") as f:
    written = toml.load(f)
assert "regreet" in written["default_session"]["command"]
