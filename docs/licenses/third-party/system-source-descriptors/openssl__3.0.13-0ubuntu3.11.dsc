-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: openssl
Binary: openssl, libssl3t64, libcrypto3-udeb, libssl3-udeb, libssl-dev, libssl-doc
Architecture: any all
Version: 3.0.13-0ubuntu3.11
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Christoph Martin <christoph.martin@uni-mainz.de>, Kurt Roeckx <kurt@roeckx.be>, Sebastian Andrzej Siewior <sebastian@breakpoint.cc>
Homepage: https://www.openssl.org/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/openssl
Vcs-Git: https://salsa.debian.org/debian/openssl.git
Testsuite: autopkgtest
Testsuite-Triggers: perl
Build-Depends: dpkg-dev (>= 1.22.5), debhelper-compat (= 13)
Package-List:
 libcrypto3-udeb udeb debian-installer optional arch=any profile=!noudeb
 libssl-dev deb libdevel optional arch=any
 libssl-doc deb doc optional arch=all
 libssl3-udeb udeb debian-installer optional arch=any profile=!noudeb
 libssl3t64 deb libs optional arch=any
 openssl deb utils optional arch=any
Checksums-Sha1:
 18b985dcd3fc0bab54cc4bfc10fa9a80ce9e345d 15294843 openssl_3.0.13.orig.tar.gz
 236c8dcb9a1c1b62e47abae363931ee9f5e63e6c 195932 openssl_3.0.13-0ubuntu3.11.debian.tar.xz
Checksums-Sha256:
 88525753f79d3bec27d2fa7c66aa0b92b3aa9498dafd93d7cfa4b3780cdae313 15294843 openssl_3.0.13.orig.tar.gz
 ebe680fe048823da7880008ebb695026adf998c933640603f73590577004f055 195932 openssl_3.0.13-0ubuntu3.11.debian.tar.xz
Files:
 c15e53a62711002901d3515ac8b30b86 15294843 openssl_3.0.13.orig.tar.gz
 186e3d828aec22d75bb6f8888e32b92f 195932 openssl_3.0.13-0ubuntu3.11.debian.tar.xz
Original-Maintainer: Debian OpenSSL Team <pkg-openssl-devel@alioth-lists.debian.net>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmonOFMACgkQZWnYVadE
vpMQhw//faj5TmkbHEOdC/k0Q3nleJ0oYXfhbcFQLMG5NQblkwN6dj3kk+wZOkyo
Lx5Q+t69pvbouZcTtxnbqSHLluyT2VeVXcKOSXGitGT3RnURCKKtQZVEqGnyAG5+
ZdusDOeVWCN4GzFdvMa4r6OkSjqges2NHh5JbzKYgSPoZM3P+9HoGjvvhhaiNv4K
JNf9T5LfADMOgiEQ3p27JIZZWoc9sKvtyooeXmQ7eabs6sYswicvJU1qYkLCWE8h
V8Xx0PF1E9TNiezToJjMtPwSIR7T3Bpsp/UOWQ0ZXobum9imyr0fEiYStEuiIVbd
tmiYtzYJca2kh0aqTMud100HF/aPPvVEYixRbCGLNVLBeUkXQFD8WTftc2En9NKZ
Ctvwxp5gxma/R24m/xA65qyzuAqJ+DcUBJQEXSxKCNA38Glnix8hoFR03JzGp5+m
naIVESQQDkvIjbF1wEruYuHLDauX8ThKwJs5QnpMvrTaM+xDmDRK5dheJQyVby9R
cnAB2MHAGfXCY8H2CLoyPb+YL+QbfkL9s+jflhS4x3A36WGYnkc7VJi02nzLTuKA
0MA3oZJOLJI0GNObBZ8ueSdG1A+/i8T3rmGopf4QMhycIN5B0jkH+71YhiVB/Oyd
cwStmNtQxvfD20x4MOhjXEF8iKpZhZnhVA3W/hbRz20Euv7KO7E=
=sQ0+
-----END PGP SIGNATURE-----
