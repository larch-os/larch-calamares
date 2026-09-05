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
#
# Also seeds the installer-created user's zsh/niri/noctalia config.
# Deliberately not done via /etc/skel (which stays plain Arch default,
# see larch-base's build-local-repo.sh) -- this is for the one user
# Calamares creates here, not every future `useradd`. Copied straight
# from the live "larch" user's home, then install-overrides/ (shipped
# in the squashfs alongside it) is layered on top for anything that
# has to differ once Calamares itself is gone from the installed
# system -- e.g. noctalia's bar losing the install button.

import os
import shutil

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


# Bash's own skel (plain Arch default) already gave the new user these
# via useradd -m; copying them from the live user would just clobber
# that with whatever the live session happens to have.
SKIP_FROM_LIVE_HOME = {".bash_logout", ".bash_profile", ".bashrc"}


def seed_user_config(root_mount_point, user):
    """
    Copies /home/larch's dotfiles into the new user's home, skipping
    the bash files (see SKIP_FROM_LIVE_HOME), then layers
    /usr/share/larch/install-overrides/ on top.
    """
    if not user:
        return

    live_home = os.path.join(root_mount_point, "home/larch")
    target_home = os.path.join(root_mount_point, "home", user)
    if not os.path.isdir(live_home) or not os.path.isdir(target_home):
        return

    for entry in os.listdir(live_home):
        if entry in SKIP_FROM_LIVE_HOME:
            continue
        source = os.path.join(live_home, entry)
        dest = os.path.join(target_home, entry)
        if os.path.isdir(source):
            shutil.copytree(source, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(source, dest)

    overrides_dir = os.path.join(root_mount_point, "usr/share/larch/install-overrides")
    if os.path.isdir(overrides_dir):
        for dirpath, _dirnames, filenames in os.walk(overrides_dir):
            rel = os.path.relpath(dirpath, overrides_dir)
            dest_dir = target_home if rel == "." else os.path.join(target_home, rel)
            os.makedirs(dest_dir, exist_ok=True)
            for name in filenames:
                shutil.copy2(os.path.join(dirpath, name), os.path.join(dest_dir, name))

    ret = libcalamares.utils.target_env_call(
        ["chown", "-R", "{0}:{0}".format(user), "/home/{}".format(user)]
    )
    if ret != 0:
        libcalamares.utils.warning(
            "Failed to chown /home/{} after seeding config (exit {})".format(user, ret))


def run():
    """
    Post-install setup for selected optional extras.
    """
    root_mount_point = libcalamares.globalstorage.value("rootMountPoint")
    packages = selected_packages()
    user = libcalamares.globalstorage.value("username")

    seed_user_config(root_mount_point, user)

    if "docker" in packages:
        enable_service("docker")
        if user:
            add_user_to_group(user, "docker")

    if "incus" in packages:
        enable_service("incus")
        if user:
            add_user_to_group(user, "incus-admin")

    return None
