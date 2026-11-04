-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: openssl
Binary: openssl, libssl3t64, libcrypto3-udeb, libssl3-udeb, libssl-dev, libssl-doc
Architecture: any all
Version: 3.0.13-0ubuntu3.16
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
 c6a77f33be7b3fcc923e39bd4d2029fb57803b55 223332 openssl_3.0.13-0ubuntu3.16.debian.tar.xz
Checksums-Sha256:
 88525753f79d3bec27d2fa7c66aa0b92b3aa9498dafd93d7cfa4b3780cdae313 15294843 openssl_3.0.13.orig.tar.gz
 77893129922c917792dd187c2853fb36ce1c98597c442b42d8190252959b7f6c 223332 openssl_3.0.13-0ubuntu3.16.debian.tar.xz
Files:
 c15e53a62711002901d3515ac8b30b86 15294843 openssl_3.0.13.orig.tar.gz
 6dc3d59f4fc450f3d864c5df0973420e 223332 openssl_3.0.13-0ubuntu3.16.debian.tar.xz
Original-Maintainer: Debian OpenSSL Team <pkg-openssl-devel@alioth-lists.debian.net>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmqzw9EACgkQZWnYVadE
vpMRXA/8DbnTPUYbI9wpNnyHOZ8TxRBKnOTag3a+pKL4k1iLi7eOuzX1AHbGAD9t
h7WHtjD1dPh4gN0Z6a7MXcuoVeLuA9oOCL9pRt6RoKMZQ9bjkHZ0ufJOfTh2yT9W
w50VULXGVvTUv6mXCAlC/RALK7+4WdQ76E+DXEvaG9z7LftM31uvKU1ThqbwNePx
FJSSLkfeAc/NmFhnhKNIEwkgqfTJd/T1Lp0CZpZ9F6w5hnYMXW8oqsDetj3lkJ4w
hzAEwagZj/TMsptpHm2xIntp6+XHc2btJr3rCzVs0mHeh7B9eXmyWiY8HnXboevp
K8lJrkHB6s+x8WAxXDEbOoH5eDttyQW0xPTe6IHzsBh4iC5Vpxd0ykybBQgqGYn9
2BBaHSnkjXQLq6RZgqvweW091JNZZPsuYp0440ar+TQ5kfXGtzQfMwA0jjDVhCWN
1VXh3KSLKm/IPMnUzHmH0+GtDKZOO6Qg+TBYzjCa0NWGJRHMhZ2GPPAtlRKvJ0Pg
ZPU111jQan3wLVaTVszXM7P8S/QERqzXPpfAhSaR32g7nkdOyWk8yEjLvde6/8tJ
UrO9xNoRpnLh+smNbCWgLnJExNo+4kp04Or75VWOKdl0ymsQUohatJU5P6jIUwt/
lrz44aojvwemAniuVzRJNQX6vksEk3SKP8SxAlCkfurORSMWgiw=
=w7us
-----END PGP SIGNATURE-----
