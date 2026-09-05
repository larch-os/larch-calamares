#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Larch ===
#
# larch-base's squashfs is both the live-boot medium and the source
# unpackfs copies onto the install target. Anything built for booting
# the live ISO (rather than the eventual installed system) ships into
# the target unchanged unless a step here undoes it first. Each step
# below is one such artifact: what it is, why it's live-only, and what
# breaks if it's left in place. Add new steps here as more are found --
# don't just grow one function.
#
# Must run after unpackfs (needs the target filesystem to exist) and
# before initcpiocfg/initcpio (the initramfs must be built with clean
# config, not the live one).

import os
import shutil

import libcalamares

import gettext
_ = gettext.translation("calamares-python",
                        localedir=libcalamares.utils.gettext_path(),
                        languages=libcalamares.utils.gettext_languages(),
                        fallback=True).gettext

STANDARD_LINUX_PRESET = """# mkinitcpio preset file for the 'linux' package

ALL_kver="/boot/vmlinuz-linux"

PRESETS=('default' 'fallback')

default_image="/boot/initramfs-linux.img"

fallback_image="/boot/initramfs-linux-fallback.img"
fallback_options="-S autodetect"
"""

BOOT_MEDIA_DIR = "/run/archiso/bootmnt/larch/boot/x86_64"


def _remove_if_exists(path):
    if os.path.exists(path):
        os.remove(path)
        libcalamares.utils.debug("Removed live-only {}".format(path))


def _remove_archiso_mkinitcpio_hooks(root_mount_point):
    """
    /etc/mkinitcpio.conf.d/archiso.conf overrides HOOKS to archiso's
    live-only list (archiso, archiso_loop_mnt, the archiso_pxe_* hooks,
    memdisk). A .conf.d drop-in entirely *replaces* HOOKS rather than
    merging it, so it silently wins over whatever initcpiocfg correctly
    computed (e.g. dropping `encrypt` for a LUKS install) once
    initcpio's mkinitcpio -P actually runs. Left in place: boots into
    GRUB fine, then can't unlock or find root.
    """
    _remove_if_exists(os.path.join(root_mount_point, "etc/mkinitcpio.conf.d/archiso.conf"))


def _restore_standard_mkinitcpio_preset(root_mount_point):
    """
    /etc/mkinitcpio.d/linux.preset is archiso's own live-build preset:
    PRESETS=('archiso'), no default/fallback at all, and it points
    mkinitcpio -P at archiso.conf directly, bypassing initcpiocfg's
    corrected /etc/mkinitcpio.conf entirely. Replaced with the standard
    linux package preset (default + fallback).
    """
    linux_preset = os.path.join(root_mount_point, "etc/mkinitcpio.d/linux.preset")
    with open(linux_preset, "w") as f:
        f.write(STANDARD_LINUX_PRESET)
    libcalamares.utils.debug("Restored standard default/fallback {}".format(linux_preset))


def _restore_kernel_and_initramfs(root_mount_point):
    """
    /boot is empty in the squashfs entirely: mkarchiso pacstraps the
    linux package (which does put a kernel at /boot/vmlinuz-linux), but
    then moves the kernel/initramfs out to the ISO's own boot media
    before building the squashfs, to avoid shipping it twice (once
    compressed in the squashfs, once for the bootloader to load
    directly) -- confirmed by mounting a built ISO. unpackfs alone
    never gives the install target a kernel; mkinitcpio then fails
    outright: "-k /boot/vmlinuz-linux must be readable". Copied back in
    from the live boot media, mounted at /run/archiso/bootmnt/ for the
    session (same path convention as unpackfs.conf's own source).
    """
    for name in ("vmlinuz-linux", "initramfs-linux.img"):
        source = os.path.join(BOOT_MEDIA_DIR, name)
        target = os.path.join(root_mount_point, "boot", name)
        if not os.path.exists(source):
            return (
                _("Boot media not found"),
                _("Expected the live kernel at <pre>{}</pre> but it doesn't "
                  "exist. Are you running from the actual ISO (not calamares "
                  "-d on a bare desktop)?").format(source),
            )
        shutil.copy(source, target)
        libcalamares.utils.debug("Copied {} -> {}".format(source, target))
    return None


def _strip_sddm_autologin(root_mount_point):
    """
    /etc/sddm.conf.d/00-larch.conf's [Autologin] section logs straight
    into the "larch" live user -- convenient for the live session,
    wrong for the installed system, which has a real user and should
    show a login screen. Only [Autologin] is stripped; [General] and
    [Theme] (virtual keyboard, silent SDDM theme) are still wanted on
    the installed system, so the file itself stays.
    """
    sddm_conf = os.path.join(root_mount_point, "etc/sddm.conf.d/00-larch.conf")
    if not os.path.exists(sddm_conf):
        return
    with open(sddm_conf) as f:
        lines = f.readlines()
    if "[Autologin]\n" not in lines:
        return
    start = lines.index("[Autologin]\n")
    end = start + 1
    while end < len(lines) and not lines[end].startswith("["):
        end += 1
    del lines[start:end]
    with open(sddm_conf, "w") as f:
        f.writelines(lines)
    libcalamares.utils.debug("Removed live-only [Autologin] section from {}".format(sddm_conf))


def _remove_getty_autologin(root_mount_point):
    """
    /etc/systemd/system/getty@tty1.service.d/autologin.conf logs in as
    root on the tty1 console -- also live-session-only convenience, no
    installed-system equivalent wanted.
    """
    _remove_if_exists(os.path.join(
        root_mount_point, "etc/systemd/system/getty@tty1.service.d/autologin.conf"
    ))


# Run in order. Each step takes root_mount_point and returns None on
# success, or a (title, details) tuple to fail the whole job -- matching
# the Calamares job contract, since this list is run() itself.
STEPS = (
    _remove_archiso_mkinitcpio_hooks,
    _restore_standard_mkinitcpio_preset,
    _restore_kernel_and_initramfs,
    _strip_sddm_autologin,
    _remove_getty_autologin,
)


def pretty_name():
    return _("Cleaning up live-medium-only boot configuration.")


def run():
    root_mount_point = libcalamares.globalstorage.value("rootMountPoint")
    for step in STEPS:
        error = step(root_mount_point)
        if error:
            return error
    return None
