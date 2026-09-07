# Diff from upstream Calamares

What actually changed, file by file, since we forked from
[`v3.4.2`](https://codeberg.org/Calamares/calamares/src/tag/v3.4.2). For
*why*, see `LARCH.md`. To regenerate/verify this list:

```
git fetch upstream tag v3.4.2
git diff --stat v3.4.2...HEAD
```

## New

| Path | What it is |
|---|---|
| `src/branding/larch/` | Our branding component (logo, wallpaper, QSS, slideshow) -- what `settings.conf` actually points at. `default/` is upstream's untouched example. |
| `src/modules/larch-preinstall/` | Strips live-only boot config (archiso mkinitcpio hooks, autologin) from the target before install continues. |
| `src/modules/larch-postinstall/` | Per-package setup (services, groups) for optional extras; seeds the new user's dotfiles. |
| `src/modules/netinstall/larch-essentials.conf` | Second `netinstall` instance: default-selected, opt-out recommended tooling. |
| `PKGBUILD` | Builds this repo directly from git, not a release tarball. |

## Removed

| Path | Why |
|---|---|
| `src/modules/netinstall/netinstall.yaml` | Upstream's standalone example groups file; superseded by `netinstall.conf`/`larch-essentials.conf`. Its own test (`ItemTests::testExampleFiles`) still expects it and fails -- known gap, not yet cleaned up. |
| `.github/workflows/*` (renamed to `workflows-disabled/`) | CI not run in this fork. |

## Modified

| Path | What changed |
|---|---|
| `settings.conf` | `grubcfg` uncommented; `instances:` adds the `larch-essentials` netinstall instance; sequence includes both netinstall instances. |
| `src/modules/partition/partition.conf` | Encryption on by default (opt-out); separate unencrypted `/boot` partition; swap list trimmed to `none` (zram handles swap instead). |
| `src/modules/users/users.conf` | Shell is `/usr/bin/zsh`, not `/bin/bash`; libpwquality requirements removed entirely (not just zeroed -- see LARCH.md for why zeroing alone doesn't work). |
| `src/modules/unpackfs/unpackfs.conf` | Points at larch-base's real squashfs (`/run/archiso/bootmnt/...`) instead of upstream's example sources. |
| `src/modules/packages/packages.conf` | `try_remove: larch-calamares` post-install; `skip_if_no_internet` for optional extras. |
| `src/modules/shellprocess/shellprocess.conf` | Upstream's 4-command example replaced with our real pacman-keyring-init script (2 commands) -- invalidates upstream's own test, known gap. |
| `src/modules/netinstall/netinstall.conf` | "Extras" group added: docker/incus/chromium, opt-in. |
| `src/modules/netinstall/Config.{h,cpp}` | `Status::NoInternet` + async `checkInternet()` (re-probes on each page visit, keeps `globalStorage["hasInternet"]` in sync). |
| `src/modules/netinstall/NetInstallPage.cpp` | Disables the package tree while `NoInternet`. |
| `src/modules/netinstall/NetInstallViewStep.cpp` | Calls `checkInternet()` on every `onActivate()`, not just once. |
| `src/modules/netinstall/PackageModel.cpp` | Checkbox toggle now visually updates immediately. |
| `src/modules/displaymanager/displaymanager.conf` | Only `greetd` listed; explicit `defaultDesktopEnvironment` (niri); `basicSetup: true`; `greeter_user`/`greeter_group` set to `greeter`. |
| `src/modules/displaymanager/main.py` | `DMgreetd` gained a ReGreet branch (upstream only knows gtkgreet/tuigreet/ddlm/agreety). |
| `src/libcalamares/network/Manager.cpp` | `checkHasInternet()` given an 8s timeout -- upstream's default has none, so a real-but-unreachable network could hang 60s+. |
| `src/modules/locale/Config.cpp` | Same timeout fix, for `startGeoIP()`'s synchronous ping (runs on the GUI thread -- worse hang than the one above). |
| `data/images/*.svg`, `*.svgz` | Icons recolored to match our palette. |
| `src/branding/CMakeLists.txt` | Adds the `larch` branding subdirectory alongside upstream's `default`. |
