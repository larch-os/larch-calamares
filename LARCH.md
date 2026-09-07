# Larch notes

This is Larch's fork of Calamares: upstream code untouched, branding/config/
modules changed for Larch. This file is the accumulated knowledge from
building it — not a tutorial, a reference. Read this before touching
anything below.

## Remotes

- `origin` = `git@github.com:larch-os/larch-calamares.git` (ours, push here)
- `upstream` = `https://codeberg.org/Calamares/calamares.git` (real upstream)

Do NOT use `github.com/calamares/calamares` as upstream — it's a stale
mirror. It was missing `v3.4.0`/`v3.4.2` when `codeberg.org/Calamares/calamares`
already had them. Confirmed by fetching both and comparing tags.

Currently pinned to `v3.4.2` + our commits on `main`.

## Staying in sync with upstream

Two separate problems, not one:

**Our commits reaching the built package** — already automatic. `PKGBUILD`'s
`pkgver()` derives from `git describe`-style output (commit count + short
hash), and `larch-base/scripts/prepare-iso.sh` does `git pull --ff-only`
on this repo before every `makepkg`. Push to `main`, next ISO build picks it
up. The only failure mode is a human forgetting to re-run that script before
`mkarchiso` — it's not automatic on its own.

**Upstream's commits reaching us** — manual, periodic:
1. `git fetch upstream --tags`
2. `git merge upstream/vX.Y.Z` (a real tag, not `upstream/main` — stay on
   stable cuts). Merge, don't rebase — we're past the initial pin, rebasing
   now would force-push over published history.
3. Our diff against upstream is narrow: new files (branding/, larch-postinstall/,
   PKGBUILD, this file) plus small edits to `unpackfs.conf`, `packages.conf`,
   `partition.conf`, `settings.conf`, `shellprocess.conf`,
   `netinstall/PackageModel.cpp`, `netinstall/Config.{h,cpp}`,
   `netinstall/NetInstallPage.cpp`, `netinstall/NetInstallViewStep.cpp`,
   `libcalamares/network/Manager.cpp`, `locale/Config.cpp`,
   `displaymanager/displaymanager.conf`, `displaymanager/main.py`, and a
   dozen `data/images/*.svg` icons. Conflicts, if any, will be in that
   list — nowhere else.
4. Rebuild and smoke-test before pushing (see "Build" below). At minimum:
   does it still compile, do our config keys still exist (upstream can
   rename/remove config options between releases).

No fixed cadence decided yet — pick one up when a specific fix/CVE is worth
having, or check periodically. Not automated.

## Build

Runtime deps: `kcoreaddons kpmcore libpwquality qt6-declarative qt6-svg yaml-cpp`
Build deps: `extra-cmake-modules libglvnd ninja qt6-tools qt6-translations git boost cmake`

```sh
cmake -S . -B build -G Ninja -DWITH_QT6=ON
cmake --build build
```

Two real gotchas, both cost real time to find:

1. **Config files only get copied into `build/` at CMake *configure* time,
   not build time.** Editing a `.conf`, `settings.conf`, or `branding.desc`
   and running `cmake --build build` alone does nothing — you'll test
   against stale content. Always `cmake -S . -B build` again first after
   editing any config file. `ninja: no work to do` with no actual rebuild is
   the tell.
2. **Modules are separate plugin targets, not linked into `calamares`.**
   `cmake --build build --target calamares` only rebuilds the main binary +
   libcalamares/libcalamaresui — it will NOT recompile a module you just
   edited (e.g. `PackageModel.cpp`). Build the default target
   (`cmake --build build`, no `--target`) to actually recompile modules.

## Running it (`-d` debug mode)

Must run from the build dir — debug mode resolves config/branding relative
to the current working directory:

```sh
cd build
QT_QPA_PLATFORMTHEME=qt6ct HOME=/root ./calamares -d
```

- `QT_QPA_PLATFORMTHEME=qt6ct` — without it, Qt falls back to its default
  light palette regardless of branding.desc's colors. niri sets this in its
  own `environment {}` block for processes it spawns directly, but a
  process launched from an unrelated shell (a different session, or
  `qemu-guest-agent`'s `guest-exec`) won't have it.
- `HOME=/root` (or whatever's actually correct) — needed for the same
  reason if launching via a spawn mechanism that doesn't set it (confirmed:
  `qemu-guest-agent`'s `guest-exec` spawns with `HOME` completely empty).
  Without it, qt6ct can't find `~/.config/qt6ct/qt6ct.conf` even if the file
  exists and the platform theme is set correctly.
- Real disk/partition testing needs real root + a real block device — not
  meaningful on a bare desktop session. Use a VM with an attached disk.

## Architecture decisions (and why)

- **Login manager = greetd + ReGreet, not SDDM.** Chosen over gtkgreet/
  tuigreet specifically because ReGreet natively supports a background
  image + fit mode + a separate CSS override file
  (`/etc/greetd/regreet.{toml,css}`, shipped statically by `larch-base`'s
  airootfs, same as the GRUB theme) — matching "looks ours, minimal but
  aesthetic" with far less hand-rolled CSS than restyling gtkgreet's bare
  widget from scratch. `displaymanager/main.py`'s `DMgreetd.set_autologin()`
  has no branch for regreet upstream — this is the first *Python*-module
  patch to this fork (previously only C++: `libcalamares/network/Manager.cpp`,
  `locale/Config.cpp`), same forked/documented/not-upstream-contributed
  precedent. Checked *before* the existing gtkgreet branch; for Larch this
  never matters in practice since gtkgreet is never installed.

  Two non-obvious, easy-to-accidentally-revert requirements this depends
  on, both in `displaymanager.conf`:
  - **`defaultDesktopEnvironment`** (`executable: /usr/bin/niri`,
    `desktopFile: niri`) — niri isn't in `main.py`'s hardcoded
    `desktop_environments` list (Hyprland and sway are, niri isn't), so
    `find_desktop_environment()` returns `None` for it, and
    `DMgreetd.set_autologin()` has no `None`-guard on
    `default_desktop_environment` (unlike `DMsddm`). Without this key set
    explicitly, installing crashes the first time `displaymanager` runs.
  - **`basicSetup: true`** — gates whether `DMgreetd.basic_setup()` (which
    would `useradd`/`groupadd` the greeter account) runs at all. In
    practice this is a no-op either way: greetd's own Arch package ships
    a `sysusers.d` fragment (`u greeter - "greetd greeter user" - /bin/bash`,
    no explicit group, so sysusers defaults to a same-named `greeter`
    group) applied automatically the moment `greetd` is pacstrapped, via
    the `systemd-sysusers` pacman hook — so the account already exists
    before Calamares ever runs. `greeter_user`/`greeter_group` in the
    `greetd:` config block are set to `"greeter"`/`"greeter"` to match
    that real account, not Calamares' own class default (`"greetd"` for
    the group) or the placeholder values (`tom_bombadil`/`wheel`) this
    file had before anything used it for real.

  Autologin parity: live-boot autologin straight into niri (the "larch"
  user) is preserved unchanged via `larch-base`'s
  `/etc/greetd/config.toml` `[initial_session]`, same as SDDM's old
  `[Autologin]` section. `larch-preinstall`'s `_strip_greetd_autologin`
  (replacing the old `_strip_sddm_autologin`) removes that section before
  install, as defense-in-depth in case a later module aborts the install
  — `displaymanager` itself also removes autologin when the user didn't
  check "log in automatically", but that runs much later in the exec
  sequence.
- **Base install = `unpackfs` unsquashing larch-base's actual live squashfs**
  (`/run/archiso/bootmnt/larch/x86_64/airootfs.sfs`, confirmed by mounting a
  built ISO and checking `/usr/share/archiso`'s own boot-hook conventions),
  not a pacman/netinstall-based base install. `larch-base`'s `mkarchiso`
  build pacstraps packages then copies the `airootfs/` overlay on top, so
  this one unsquash carries packages + all our dotfiles/config together.
- **`packages` module (pacman backend) is for optional extras only**
  (docker/incus/chromium, picked via the `netinstall` page), never the base
  system. `skip_if_no_internet: true` — these are optional, missing network
  shouldn't fail the whole install.
- **`netinstall` runs twice, as two separate module *instances*.** The
  plain `netinstall` instance (`netinstall.conf`, sidebar "Extra
  Software") is opt-in extras (docker/incus/chromium — `selected: false`).
  A second instance, `netinstall@larch-essentials`
  (`netinstall/larch-essentials.conf`, sidebar "Larch Essentials"), is
  Larch's own recommended tooling (chezmoi, pass, pika-backup, htop,
  btop, lazygit, uv, k3d-bin, kubectl, herdr-bin) — `selected: true`,
  opt-out instead of opt-in. Both are declared in `settings.conf`'s
  `instances:` section (a custom `id` needs an explicit `config:` key,
  or it'd try to reuse `netinstall.conf`) and both appear in the
  `sequence`. This reuses the *same* compiled `netinstall` plugin —
  Calamares instantiates one `Config`/`ViewStep` per instance
  (`ViewModule::loadSelf()` calls the plugin factory once per module
  instance, then `setModuleInstanceKey()` stamps each with its own key)
  — so the `NoInternet`/timeout fixes below apply to both automatically,
  and each instance's selections land in `globalStorage`'s
  `packageOperations` under its own `source` key
  (`netinstall@netinstall` vs `netinstall@larch-essentials`), so they
  don't clobber each other. No new C++ module needed for this — see the
  git history for why a from-scratch plugin was considered and rejected
  (this is functionally identical from the packages module's point of
  view, and config-only changes are trivially editable when the
  essentials list needs to grow or shrink later).
  `packages.conf` used to `try_install` chezmoi/pass/pika-backup
  unconditionally (no user choice at all) — moved into
  `larch-essentials.conf` instead so they're visible and declinable,
  same as any other extra.
  paru-bin deliberately stays out of both instances — it lives in
  `larch-base`'s `packages.x86_64` (live *and* installed, since that's
  one shared squashfs), so it's usable to build AUR packages during the
  install itself, not just after a reboot.
- **Swap = zram only.** `partition.conf`'s `userSwapChoices: [none]` — no
  swap UI at all. Actual zram setup (package + `/etc/systemd/zram-generator.conf`)
  lives in `larch-base`'s airootfs, not here; it carries over via the
  squashfs like everything else.
- **Encryption defaults on, opt-out.** `preCheckEncryption: true`.
  `partition.conf`'s `partitionLayout` gives `/boot` its own partition
  with `noEncrypt: true`, kept separate from the LUKS root, so GRUB never
  needs `GRUB_ENABLE_CRYPTODISK` to read it. `larch-base`'s
  `/etc/default/grub` deliberately does *not* set that key statically —
  `grubcfg` (see below) computes it per-install and patches the file in
  place. `initcpiocfg/main.py` auto-detects `luksMapperName` on root and
  adds the `encrypt` mkinitcpio hook.

  Earlier iteration had no `partitionLayout` at all (single root
  partition, ESP only), so `/boot` ended up *inside* the encrypted root.
  `grub-install` failed outright then: "attempt to install to encrypted
  disk without cryptodisk enabled". Setting `GRUB_ENABLE_CRYPTODISK=y`
  statically fixed *that*, but uncovered the real bug one layer down: the
  `encrypt` mkinitcpio hook had no `cryptdevice=` kernel parameter to act
  on, because upstream's `grubcfg` module — which writes that parameter,
  and which is the only thing that should ever set
  `GRUB_ENABLE_CRYPTODISK` — was commented out in `settings.conf` (it's
  been commented out since upstream's 2015 sample template, not something
  we did). Without `cryptdevice=`, mkinitcpio just tried to mount root by
  its raw filesystem UUID, which isn't visible until LUKS is unlocked:
  "device not found" in an emergency shell, confirmed via a real boot
  attempt. Fixed by uncommenting `grubcfg` (runs right before
  `bootloader`) and switching to the separate-`/boot`-partition layout in
  the same pass — `grubcfg` already has an `unencrypted_separate_boot`
  check that does the right thing for either layout.
- **Bootloader = GRUB only**, no theme config here. `bootloader.conf`'s
  `efiBootLoader: "grub"` is the only entry (not a fallback list). The
  actual GRUB theme (`/etc/default/grub`, `/boot/grub/themes/larch/`) lives
  in `larch-base`'s airootfs — `grub-mkconfig` just reads whatever's
  already in the target, so it comes along for free via the squashfs.
- **`larch-postinstall`** (our own module) exists because `packages.conf`'s
  `pre-script`/`post-script` can't do per-package setup (enable a service,
  add the installed user to a group): they're `str.split(" ")`'d with no
  variable substitution and no username access — can't run compound shell
  commands or know who the target user is. `larch-postinstall` reads
  globalStorage's `packageOperations` key directly (same key `netinstall`
  writes) instead.

  Also seeds the installer-created user's zsh/niri/noctalia config,
  copied straight from the live "larch" user's home (skipping the bash
  files, since `useradd -m` already gave the new user those from
  `/etc/skel`), with `larch-base`'s `install-overrides/` (shipped in the
  squashfs at `/usr/share/larch/install-overrides/`) layered on top for
  anything that has to differ once Calamares itself is gone from the
  installed system — e.g. noctalia's bar losing the `install_larch`
  button. Deliberately **not** done via `/etc/skel`: skel stays plain
  Arch default (just whatever `bash`/`screen` put there), since Larch's
  setup is only for the live user and this one installer-created user,
  not every future `useradd`. (Earlier iteration populated `/etc/skel`
  directly from `/home/larch` in `prepare-iso.sh` — reverted; it
  worked, but affected any future manually-`useradd`'d account too,
  which wasn't the intent, and it also had a real bug: noctalia's
  seeded `settings.toml` still hardcoded `/home/larch/...` paths, found
  via a real install where the new user's wallpaper didn't show.)
  `packages.conf` also `try_remove`s `larch-calamares` itself — no
  reason to keep an installer around post-install — and `users.conf`'s
  `user.shell` is `/usr/bin/zsh`, not the Calamares default `/bin/bash`.
- **`larch-preinstall`** (our own module, runs right after `unpackfs`)
  strips two live-boot-only files that `unpackfs` otherwise carries
  straight into the install target unchanged: `/etc/mkinitcpio.conf.d/
  archiso.conf` (overrides HOOKS to archiso's live-only list — a
  `.conf.d` drop-in *replaces* HOOKS, doesn't merge, so it silently wins
  over whatever `initcpiocfg` correctly computes, e.g. dropping the
  `encrypt` hook on a LUKS install even though `initcpiocfg` added it)
  and `/etc/mkinitcpio.d/linux.preset` (archiso's own preset —
  `PRESETS=('archiso')`, no `default`/`fallback` at all, and it points
  `mkinitcpio -P` at `archiso.conf` directly). Left in place, the
  target boots into GRUB fine and then can't unlock/find root — this
  is almost certainly what "installer failing around grub and
  mkinitcpio" on real hardware actually was. Must run before
  `initcpiocfg`/`initcpio` regenerate the initramfs, obviously.

  Also copies the kernel itself back in: `/boot` is completely empty
  in the squashfs (confirmed by mounting a built ISO and checking) --
  mkarchiso moves the kernel/initramfs out to the ISO's own boot media
  (`larch/boot/x86_64/`) before building the squashfs, so it isn't
  duplicated once compressed-in-squashfs and once for the bootloader
  to load directly. Without this, `mkinitcpio` fails outright:
  `-k /boot/vmlinuz-linux must be readable`. Copied from
  `/run/archiso/bootmnt/larch/boot/x86_64/` (the live boot media,
  mounted there for the session) -- same path convention as
  `unpackfs.conf`'s own source.

  Also strips two live-only autologin mechanisms that unpackfs
  otherwise carries into the target unchanged: `00-larch.conf`'s
  `[Autologin]` SDDM section (auto-logs into the "larch" live user --
  wrong once a real user exists; only that section is stripped, the
  rest of the file, e.g. the silent theme, is still wanted) and
  `getty@tty1.service.d/autologin.conf` (root autologin on the tty1
  console, removed outright, no installed-system equivalent wanted).
  Found via a real install: the installed system dropped straight into
  a desktop session with no login prompt, same as the live ISO.

## Bugs already found and fixed (don't reintroduce these)

- **QSS `background-color` without `color`.** `stylesheet.qss` had
  `#mainApp { background-color: #1e1e2e; }` with no `color:`. Any QSS rule
  on a widget makes Qt's style-sheet cascade take over color resolution for
  its descendants too — without an explicit `color`, text falls back to
  black. Black text on a dark background is invisible. If you add container
  background rules, always pair with an explicit `color`, or don't set
  background at all and trust the system palette.
- **`PackageModel::setData()`'s `dataChanged()` doesn't cover nested rows.**
  Toggling a group checkbox (e.g. `netinstall`'s "Extras" group) correctly
  updates the underlying selection via `setSelected()`'s cascade, but the
  emitted `dataChanged()` range only covers sibling rows at the *same tree
  level* as the clicked item — nested child rows never get told to
  repaint, so they show stale checkboxes despite correct underlying state.
  Fixed with `emit layoutChanged()` instead (fine for a tree this small).
- **Bundled `data/images/*.svg` icons are dark, for a light background.**
  `#4d4d4d`, `#31363b`, `#3b3a40` recur across the partition/welcome icons
  as the "structural" color — invisible against a dark theme. Recolored the
  ones we ship to `#cdd6f4`. If upstream adds new icons or a merge brings
  more of these in, check `grep -oE 'fill:#[0-9a-fA-F]{3,6}' data/images/*.svg`
  for the same pattern.
- **GRUB `boot_menu`'s `item_color`/`selected_item_color` are TEXT colors,
  not backgrounds.** No plain solid highlight-box property exists for the
  selected item — only the pixmap-based `selected_item_pixmap_style`, which
  needs real 9-patch image assets we don't have. Setting
  `selected_item_color` to a dark color (intending it as a background) would
  have made the selected item's text invisible. Use a bright accent color
  for selected-item text instead, or build real pixmap assets later.
- **`INSTALL_CONFIG` CMake option defaults `OFF`.** Without
  `-DINSTALL_CONFIG=ON`, none of our module `.conf` files or the top-level
  `settings.conf` get installed by `cmake --install` / packaging — branding
  installs unconditionally (different code path), configs do not. Already
  set in `PKGBUILD`; don't drop it.
- **`initramfs` module is Debian, not Arch.** `InitramfsJob.cpp` hardcodes
  a call to `update-initramfs` (Debian's `initramfs-tools` command) —
  doesn't exist on Arch at all. It's a distro-specific alternative to what
  `initcpio` already does correctly for us via `mkinitcpio`, not something
  to run alongside it. Confirmed via a real install: `initcpio` succeeded
  earlier in the same sequence, then `initramfs` failed with exit 127,
  "No such file or directory". Was in our `settings.conf` sequence by
  mistake (I saw it listed and assumed it was needed without checking what
  it does) — removed from the sequence, and re-added to `PKGBUILD`'s
  `SKIP_MODULES` to match the AUR reference now that we don't use it.

- **`passwordRequirements.libpwquality` enforces a de facto ~8-char
  minimum even with `minlen=0`/`minclass=0`.** `CheckPWQuality.cpp`
  hardcodes a rejection threshold of 40 on libpwquality's *quality
  score* (entropy-based), independent of the individual
  minlen/minclass/etc. settings -- those only disable specific hard
  gates, not the overall score computation, and short passwords can't
  reach a score of 40 no matter how they're configured. `minLength: -1`
  alone does nothing to fix this if a `libpwquality:` key is still
  present. Fix: omit the `libpwquality` key from `passwordRequirements`
  entirely, don't just zero its sub-options.

- **Two `synchronousPing()` calls have no timeout, freezing the
  installer on a real but unreachable network** (not "no network at
  all", which fails fast) -- a genuine problem since Larch explicitly
  supports offline installs. `RequestOptions()`'s default constructor
  sets `m_timeout(-1)`, and `hasTimeout()` requires `> 0`, so no timer
  ever gets armed; the call blocks on a local `QEventLoop::exec()`
  until the OS-level TCP connect gives up (60s+, sometimes much
  longer). Two call sites hit this:
    - `libcalamares/network/Manager.cpp`'s `checkHasInternet()` (the
      welcome page's requirements check). `internet` isn't in
      `welcome.conf`'s `required` list, so this doesn't block the Next
      button once it resolves -- but it freezes the *entire welcome
      page* (a "Gathering system information…" spinner that never
      clears) until it does, which reads as "the installer doesn't
      proceed" even though, config-wise, it should have moved on
      immediately.
    - `locale/Config.cpp`'s `startGeoIP()`, worse: this one runs
      synchronously on the GUI thread (not a `QtConcurrent` worker),
      so a hang here freezes the *whole installer UI*, for a GeoIP
      timezone lookup that's purely cosmetic.
  Fixed by passing an explicit `RequestOptions( RequestOptions::Flags(), std::chrono::seconds( 8 ) )`
  at both call sites, matching the pattern `netinstall/LoaderQueue.cpp`
  already used for its own (already-async, already fine) group-list
  fetch.

- **Netinstall's package selections silently don't install when
  there's no internet, with no warning at all.** `groupsUrl: local`
  means the netinstall *page* needs no network to display groups, but
  the packages a user picks there still need real network access to
  actually install later -- `packages.conf`'s `skip_if_no_internet`
  silently skips the *entire* packages job when offline, extras
  selection included. Fixed with a new `Config::Status::NoInternet`
  (distinct from `FailedNetworkError`, which is about the group *list*
  failing to load, not this), set by a new `Config::checkInternet()`
  called from `NetInstallViewStep::onActivate()` every time the page
  is shown (not just once at startup -- connectivity can change while
  the user is on an earlier page). `NetInstallPage.cpp` disables
  `groupswidget` whenever that status is active, alongside the
  existing status-label text.

## Packaging

`PKGBUILD` (repo root) builds this repo directly via a git source, not a
release tarball. Based on the real AUR `calamares` PKGBUILD's `build()`/
`package()` (same upstream version, 3.4.2, so its CMake flags apply) --
including its `SKIP_MODULES` list unchanged (see the `initramfs` bug
above for why `initramfs`/`initramfscfg` are in there).

Built into `larch-base`'s local pacman repo by
`larch-base/scripts/prepare-iso.sh`, alongside the AUR-only packages.
Package name is `larch-calamares`; it `provides`/`conflicts` `calamares` so
it's a drop-in. Listed in `larch-base/archiso/releng/packages.x86_64`.
