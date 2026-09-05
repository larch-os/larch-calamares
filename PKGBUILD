# Maintainer: Larch <https://github.com/larch-os>
#
# Builds Larch's own fork of Calamares (branding, netinstall extras,
# larch-postinstall module) rather than upstream. Based on the AUR
# calamares PKGBUILD's build()/package() invocation (same upstream
# version, 3.4.2, so the same CMake flags apply) -- adapted to build
# from this git repo instead of a release tarball.

pkgname=larch-calamares
pkgver=3.4.2.r0.g0000000
pkgrel=1
pkgdesc="Larch's Calamares installer (branding, netinstall extras, larch-postinstall)"
url="https://github.com/larch-os/larch-calamares"
license=("GPL-3.0-or-later")
arch=('x86_64')
provides=('calamares')
conflicts=('calamares')

depends=(
  'kcoreaddons'
  'kpmcore'
  'libpwquality'
  'qt6-declarative'
  'qt6-svg'
  'yaml-cpp'
)
makedepends=(
  'extra-cmake-modules'
  'libglvnd'
  'ninja'
  'qt6-tools'
  'qt6-translations'
  'git'
  'boost'
)

source=("larch-calamares::git+https://github.com/larch-os/larch-calamares.git#branch=main")
sha256sums=('SKIP')

pkgver() {
  cd "$srcdir/larch-calamares"
  printf "3.4.2.r%s.g%s" "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

build() {
  # initramfs/initramfscfg is Debian's update-initramfs, not Arch --
  # initcpio/initcpiocfg (not skipped, used by our sequence) already
  # handle this via mkinitcpio. Matches the AUR calamares PKGBUILD's
  # own skip list here.
  local _skip_modules=(
    dracut
    dracutlukscfg
    dummycpp
    dummyprocess
    dummypython
    dummypythonqt
    initramfs
    initramfscfg
    interactiveterminal
    packagechooser
    packagechooserq
    services-openrc
  )

  local _cmake_options=(
    -B build
    -S "$srcdir/larch-calamares"
    -G Ninja
    -DCMAKE_BUILD_TYPE=Release
    -DCMAKE_INSTALL_PREFIX='/usr'
    -DCMAKE_INSTALL_LIBDIR='lib'
    -DWITH_QT6=ON
    -DINSTALL_CONFIG=ON
    -DSKIP_MODULES="${_skip_modules[*]}"
    -DBUILD_TESTING=OFF

    -DKDE_INSTALL_BINDIR=/usr/bin
    -DKDE_INSTALL_SBINDIR=/usr/sbin
    -DKDE_INSTALL_LIBDIR=/usr/lib
    -DKDE_INSTALL_LIBEXECDIR=/usr/libexec
    -DKDE_INSTALL_INCLUDEDIR=/usr/include
    -DKDE_INSTALL_LOCALSTATEDIR=/var
    -DKDE_INSTALL_SHAREDSTATEDIR=/usr/share
    -DKDE_INSTALL_DATAROOTDIR=/usr/share
    -DKDE_INSTALL_DATADIR=/usr/share
    -DKDE_INSTALL_LOCALEDIR=/usr/share/locale
    -DKDE_INSTALL_MANDIR=/usr/share/man
    -DKDE_INSTALL_INFODIR=/usr/share/info
    -DKDE_INSTALL_SYSCONFDIR=/etc

    -Wno-dev
  )

  cmake "${_cmake_options[@]}"
  cmake --build build
}

package() {
  DESTDIR="$pkgdir" cmake --install build
}
