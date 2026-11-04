-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (native)
Source: dpkg
Binary: dpkg, libdpkg-dev, dpkg-dev, libdpkg-perl, dselect
Architecture: any all
Version: 1.22.6ubuntu6.6
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Guillem Jover <guillem@debian.org>
Homepage: https://wiki.debian.org/Teams/Dpkg
Standards-Version: 4.6.2
Vcs-Browser: https://git.dpkg.org/cgit/dpkg/dpkg.git
Vcs-Git: https://git.dpkg.org/git/dpkg/dpkg.git
Testsuite: autopkgtest
Testsuite-Triggers: autoconf, build-essential, eatmydata, file, libmd-dev, pkgconf
Build-Depends: debhelper-compat (= 13), debhelper (>= 13.10~), pkgconf, gettext (>= 0.19.7), po4a (>= 0.59), libmd-dev, zlib1g-dev, libbz2-dev, liblzma-dev (>= 5.4.0), libzstd-dev (>= 1.4.0), libselinux1-dev [linux-any], libncurses-dev (>= 6.1+20180210), bzip2 <!nocheck>, xz-utils (>= 5.4.0) <!nocheck>, zstd <!nocheck>, git <pkg.dpkg.author-release>, ca-certificates <pkg.dpkg.author-release>, libmodule-build-perl <pkg.dpkg.author-release>, fakeroot <pkg.dpkg.author-testing>, gnupg <pkg.dpkg.author-testing>, cppcheck <pkg.dpkg.author-testing>, shellcheck <pkg.dpkg.author-testing>, aspell <pkg.dpkg.author-testing>, aspell-en <pkg.dpkg.author-testing>, codespell <pkg.dpkg.author-testing>, i18nspector <pkg.dpkg.author-testing>, libtest-minimumversion-perl <pkg.dpkg.author-testing>, libtest-perl-critic-perl <pkg.dpkg.author-testing>, libtest-pod-coverage-perl <pkg.dpkg.author-testing>, libtest-pod-perl <pkg.dpkg.author-testing>, libtest-spelling-perl <pkg.dpkg.author-testing>, libtest-strict-perl <pkg.dpkg.author-testing>, libtest-synopsis-perl <pkg.dpkg.author-testing>, lcov <pkg.dpkg.code-coverage>, libdevel-cover-perl <pkg.dpkg.code-coverage>
Package-List:
 dpkg deb admin required arch=any essential=yes
 dpkg-dev deb utils optional arch=all
 dselect deb admin optional arch=any
 libdpkg-dev deb libdevel optional arch=any
 libdpkg-perl deb perl optional arch=all
Checksums-Sha1:
 6e4456f18df6e48d1912b1266df1c2eb47afb4db 5548716 dpkg_1.22.6ubuntu6.6.tar.xz
Checksums-Sha256:
 7048ee31e30066ae123cdcb891cfa1ad55b2f42a4e04fca2c5db41607ae25196 5548716 dpkg_1.22.6ubuntu6.6.tar.xz
Files:
 5b05284bd9dc4879c2c30713646005e0 5548716 dpkg_1.22.6ubuntu6.6.tar.xz
Original-Maintainer: Dpkg Developers <debian-dpkg@lists.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmn7h58ACgkQZWnYVadE
vpMEXRAAi9lrtzIx+AL/HojAwHR+OcyAdzdEtcMaCuufqzeCthwtYvCmG/4UIA7Q
5X6nIfxntwpIY6I/DZjB6H56fu+YOn6v3Bl6Z/6hspd4buWpg2/akvYiOusGzmmS
6YgoF1Hk80Th3FCTcDWflFh235G9uypusDuthdrnhVal7tie0qo1ERl8soA/wW6d
ix19rt1/BftJAW6uhs04iYBYaNQMbY06Bz2hjS0tK57MGB+GknjLbxAt/sH7V8ts
qRZ5W15OzHpVjUOl0W82MOWl9nuffvX/0QJbUJhC2QTq2Loc/FpRWrALZdROvpbl
S7/851N540BGnZICGFJIQpj4SvUkOGmPaxHY5qzmx+XtXKa59IOlLE6F+jpYdTSO
yZvkYLR+Pz/i9r060CtHbqdxtXeZKFBU+ChqbMQJmIeDAGCEV4XMyv4SYnIAzsKw
Nv+9gUKKaT73Kd8TI/c4S1sSU4sxr1IIR2eUAh9+hejLkW/JZGow6T3TNOSdOckY
+dHjPFpdREakBgGmbuDVKImKra3dhYVayWyeqIDJv261HQkMaVhNMggHan0s3yzE
p9N56/H/mIHD1tINPthjq3BNOsGg2GaKtYmWH2APirZxDBXpUwOumfRR35hDocBY
fMnfN2MOdyJ8p30vtOPNyxh1Rsi7t5p5izidBrLHrXtaEpq/7M8=
=5NpT
-----END PGP SIGNATURE-----
