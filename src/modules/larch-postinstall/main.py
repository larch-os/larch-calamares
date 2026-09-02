#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Larch ===
#
# Larch-specific post-install setup for the optional extras offered on
# the netinstall page. Plain package installation (the packages module,
# pacman backend) isn't enough for these: docker and incus both need
# their service enabled and the installed user added to the right group
# before they're actually usable after first boot.
#
# Package selection comes from netinstall, which writes into
# globalStorage's "packageOperations" key (a list of
# {"install"|"try_install": [...names], "source": "netinstall"} maps --
# see Calamares::Packages::setGSPackageAdditions in libcalamares). This
# module just reads that same key to find out what was picked; it
# doesn't install anything itself, only configures what packages
# already did.

import libcalamares

import gettext
_ = gettext.translation("calamares-python",
                        localedir=libcalamares.utils.gettext_path(),
                        languages=libcalamares.utils.gettext_languages(),
                        fallback=True).gettext


def pretty_name():
    return _("Configuring extra software.")


def selected_packages():
    """
    Flattens globalStorage's packageOperations into a single set of
    package names, from both "install" and "try_install" entries,
    regardless of which module wrote them.
    """
    operations = libcalamares.globalstorage.value("packageOperations") or []
    names = set()
    for op in operations:
        for key in ("install", "try_install"):
            for pkg in op.get(key, []):
                # Packages may be plain strings or {"package": ..., ...}
                # dicts (see packages.conf) -- only care about the name.
                if isinstance(pkg, dict):
                    names.add(pkg.get("package"))
                else:
                    names.add(pkg)
    return names


def enable_service(service):
    ret = libcalamares.utils.target_env_call(["systemctl", "enable", service])
    if ret != 0:
        libcalamares.utils.warning(
            "Failed to enable {}.service (exit {})".format(service, ret))


def add_user_to_group(user, group):
    ret = libcalamares.utils.target_env_call(["usermod", "-aG", group, user])
    if ret != 0:
        libcalamares.utils.warning(
            "Failed to add {} to group {} (exit {})".format(user, group, ret))


def run():
    """
    Post-install setup for selected optional extras.
    """
    packages = selected_packages()
    user = libcalamares.globalstorage.value("username")

    if "docker" in packages:
        enable_service("docker")
        if user:
            add_user_to_group(user, "docker")

    if "incus" in packages:
        enable_service("incus")
        if user:
            add_user_to_group(user, "incus-admin")

    return None
