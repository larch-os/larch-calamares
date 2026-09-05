#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Larch ===
#
# larch-base's squashfs is both the live-boot medium and the source
# unpackfs copies onto the install target. That means its mkinitcpio
# setup -- built for booting the live ISO -- ships into the target
# unchanged unless something removes it first:
#
#   /etc/mkinitcpio.conf.d/archiso.conf
#       Overrides HOOKS to archiso's live-only list (archiso,
#       archiso_loop_mnt, the archiso_pxe_* hooks, memdisk). A .conf.d
#       drop-in entirely replaces the HOOKS array, not merges it -- so
#       even though initcpiocfg correctly computes real HOOKS (adding
#       `encrypt` for a LUKS root, etc.) and writes them into
#       /etc/mkinitcpio.conf, this drop-in overrides that when
#       initcpio's mkinitcpio -P actually runs. A LUKS-encrypted
#       install with this left in place builds an initramfs with no
#       encrypt hook -- it boots into GRUB fine, then can't unlock or
#       find root.
#
#   /etc/mkinitcpio.d/linux.preset
#       archiso's own live-build preset: PRESETS=('archiso'), no
#       default/fallback presets at all. Also bypasses initcpiocfg's
#       corrected /etc/mkinitcpio.conf by pointing at the archiso.conf
#       override directly (archiso_config=). Replaced here with the
#       standard linux package preset (default + fallback).
#
#   /boot is empty in the squashfs entirely.
#       mkarchiso pacstraps the linux package (which does put a kernel
#       at /boot/vmlinuz-linux), but then moves the kernel/initramfs
#       out to the ISO's own boot media before building the squashfs
#       -- confirmed by mounting a built ISO: airootfs.sfs's /boot is
#       genuinely empty, while larch/boot/x86_64/vmlinuz-linux exists
#       on the ISO itself, outside the squashfs. This avoids shipping
#       the kernel twice (once for the bootloader to load directly,
#       once compressed inside the squashfs) but means unpackfs alone
#       never gives the install target a kernel. mkinitcpio then fails
#       outright: "-k /boot/vmlinuz-linux must be readable". Fixed by
#       copying it back in from the live boot media, which is mounted
#       at /run/archiso/bootmnt/ for the duration of the live session
#       (same path convention as unpackfs.conf's own source).
#
#   /etc/sddm.conf.d/00-larch.conf's [Autologin] section
#       Autologin as the "larch" live user into niri -- convenient for
#       the live session, wrong for the installed system (which has a
#       real user set up by the users module and should show a login
#       screen). Only the [Autologin] section is stripped; [General]
#       and [Theme] (virtual keyboard, silent SDDM theme) are genuinely
#       wanted on the installed system too, so the file itself stays.
#
#   /etc/systemd/system/getty@tty1.service.d/autologin.conf
#       Autologin as root on the tty1 console -- also live-session-only
#       convenience. Removed outright, no installed-system equivalent
#       wanted.
#
# Must run after unpackfs (needs the target filesystem to exist) and
# before initcpiocfg/initcpio (the initramfs must be built with clean
# config, not this).

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


def pretty_name():
    return _("Cleaning up live-medium-only boot configuration.")


def run():
    root_mount_point = libcalamares.globalstorage.value("rootMountPoint")

    archiso_conf = os.path.join(root_mount_point, "etc/mkinitcpio.conf.d/archiso.conf")
    if os.path.exists(archiso_conf):
        os.remove(archiso_conf)
        libcalamares.utils.debug("Removed live-only {}".format(archiso_conf))

    linux_preset = os.path.join(root_mount_point, "etc/mkinitcpio.d/linux.preset")
    with open(linux_preset, "w") as f:
        f.write(STANDARD_LINUX_PRESET)
    libcalamares.utils.debug("Restored standard default/fallback {}".format(linux_preset))

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

    sddm_conf = os.path.join(root_mount_point, "etc/sddm.conf.d/00-larch.conf")
    if os.path.exists(sddm_conf):
        with open(sddm_conf) as f:
            lines = f.readlines()
        if "[Autologin]\n" in lines:
            start = lines.index("[Autologin]\n")
            end = start + 1
            while end < len(lines) and not lines[end].startswith("["):
                end += 1
            del lines[start:end]
            with open(sddm_conf, "w") as f:
                f.writelines(lines)
            libcalamares.utils.debug("Removed live-only [Autologin] section from {}".format(sddm_conf))

    getty_autologin = os.path.join(
        root_mount_point, "etc/systemd/system/getty@tty1.service.d/autologin.conf"
    )
    if os.path.exists(getty_autologin):
        os.remove(getty_autologin)
        libcalamares.utils.debug("Removed live-only {}".format(getty_autologin))

    return None
