-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: xz-utils
Binary: liblzma5, liblzma5-udeb, xz-utils, xzdec, liblzma-dev, liblzma-doc
Architecture: any all
Version: 5.6.1+really5.4.5-1ubuntu0.3
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Mohammed Adnène Trojette <adn+deb@diwi.org>
Homepage: https://tukaani.org/xz/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/xz-utils
Vcs-Git: https://salsa.debian.org/debian/xz-utils.git
Testsuite: autopkgtest
Testsuite-Triggers: autoconf, automake, debhelper-compat, gettext, libtool
Build-Depends: debhelper-compat (= 13), dpkg-dev (>= 1.16.2), autoconf (>= 2.64~), automake, libtool (>= 2.2), gettext, autopoint | gettext (<< 0.18-1), autopoint | cvs, po4a
Build-Depends-Indep: doxygen
Build-Conflicts: automake1.4
Package-List:
 liblzma-dev deb libdevel optional arch=any
 liblzma-doc deb doc optional arch=all
 liblzma5 deb libs optional arch=any
 liblzma5-udeb udeb debian-installer optional arch=any
 xz-utils deb utils standard arch=any
 xzdec deb utils optional arch=any
Checksums-Sha1:
 37ee68951814c3565f10ab92629d1d5173215fe0 1680520 xz-utils_5.6.1+really5.4.5.orig.tar.xz
 e72752e32057fa6cb9a94a3d954f85dd833bc23e 31672 xz-utils_5.6.1+really5.4.5-1ubuntu0.3.debian.tar.xz
Checksums-Sha256:
 da9dec6c12cf2ecf269c31ab65b5de18e8e52b96f35d5bcd08c12b43e6878803 1680520 xz-utils_5.6.1+really5.4.5.orig.tar.xz
 03f321901f6e1c56235cd7ae6a6784c104b1b1060ca3afa5a5806e345ee72e01 31672 xz-utils_5.6.1+really5.4.5-1ubuntu0.3.debian.tar.xz
Files:
 1d33e0be05c53e7a5641acf5c8b35fdd 1680520 xz-utils_5.6.1+really5.4.5.orig.tar.xz
 7ee8bafcd0659dac4b565223eca198b4 31672 xz-utils_5.6.1+really5.4.5-1ubuntu0.3.debian.tar.xz
Original-Maintainer: Jonathan Nieder <jrnieder@gmail.com>

-----BEGIN PGP SIGNATURE-----

iQHRBAEBCgA7FiEEcxdv4gCCE8W9nrt5a1+PL+d1/EgFAmodH0sdHGlhbi5jb25z
dGFudGluQGNhbm9uaWNhbC5jb20ACgkQa1+PL+d1/EhIOQv+JEEdWWCvi2PCm/kZ
ydfghDttlsohP2GoppCsgzFecNoq/xEi3V4PPcfjC6YtXZgCHvm6nz9KpPaewGIS
Hf8bjmXBB5cuXD6JRSKdNr75NYhjnNhVl2fvPnDfAhb0q5QjXcTnpfvqN0KUU69r
WgtzHmmVPiscXFsaueM4AXgsi/nrKCfNedF3V5b84WhmSxSTcfvzvY5E5b7V5G5c
En/vZ7EDyI3fcPJyy2AZj1w6H1DwwzwuzVG6mrSsSkeGxs2m472rSobr8FItq39n
O2lS7Ii4RjUM+N19pqzc3QFtUiCa2J9SRPJzgncLIn6JVLvRKd+gLdaNNJFWVaaN
iQF9h4vRgMw1njKhQ/+Q9p6QhCxQ6v677Y8lHeqGc99RsZGmhK88g6pbA2eL4Fw5
K0ZTs5Fe2NASgCi5Qfiluwtvv0YsdwdpbV/8lMBl9QZlu4rtAxq4PIDvQ7182tzf
DbjvfbR2Tuvaxm1l6UwrywTg+rlQ9vTQt968JFRNOAJN1E7X
=Fjkr
-----END PGP SIGNATURE-----
