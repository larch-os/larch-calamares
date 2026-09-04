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
# Must run after unpackfs (needs the target filesystem to exist) and
# before initcpiocfg/initcpio (the initramfs must be built with clean
# config, not this).

import os

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

    return None
