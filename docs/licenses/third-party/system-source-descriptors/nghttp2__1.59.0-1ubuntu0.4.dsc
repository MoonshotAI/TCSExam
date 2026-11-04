-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: nghttp2
Binary: libnghttp2-dev, libnghttp2-doc, libnghttp2-14, nghttp2-client, nghttp2-proxy, nghttp2-server, nghttp2
Architecture: any all
Version: 1.59.0-1ubuntu0.4
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Ondřej Surý <ondrej@debian.org>
Homepage: https://nghttp2.org/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/nghttp2
Vcs-Git: https://salsa.debian.org/debian/nghttp2.git
Testsuite: autopkgtest
Testsuite-Triggers: nginx
Build-Depends: debhelper (>= 13), debhelper-compat (= 13), libc-ares-dev, libcunit1-dev <!nocheck>, libev-dev, libjansson-dev, libjemalloc-dev [!hurd-i386], libssl-dev, libsystemd-dev, libxml2-dev, pkg-config, zlib1g-dev
Build-Depends-Indep: python3-sphinx, python3-sphinx-rtd-theme
Package-List:
 libnghttp2-14 deb libs optional arch=any
 libnghttp2-dev deb libdevel optional arch=any
 libnghttp2-doc deb doc optional arch=all
 nghttp2 deb httpd optional arch=all
 nghttp2-client deb httpd optional arch=any
 nghttp2-proxy deb httpd optional arch=any
 nghttp2-server deb httpd optional arch=any
Checksums-Sha1:
 ea1a278e07b4697f502b66a353ad8171657e6013 1055492 nghttp2_1.59.0.orig.tar.gz
 bf985928a4881a292c7b05069929755facc49048 18840 nghttp2_1.59.0-1ubuntu0.4.debian.tar.xz
Checksums-Sha256:
 0dd5c980f1262ff5f03676fd99f46f250b66c842f7d864fa1ca9f8453e5f8868 1055492 nghttp2_1.59.0.orig.tar.gz
 f9f73792cc9c1b903dac7ab6742674e275cc8fb0489c536dba644baccc777119 18840 nghttp2_1.59.0-1ubuntu0.4.debian.tar.xz
Files:
 7768dc83ead00b5833214204c2acfd5e 1055492 nghttp2_1.59.0.orig.tar.gz
 d1eef1592fcc1edb07b7e77a2086cd94 18840 nghttp2_1.59.0-1ubuntu0.4.debian.tar.xz
Original-Maintainer: Tomasz Buchert <tomasz@debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmpD/wQACgkQZWnYVadE
vpNyRA/9GovfQY3XjBh2xnH/ufznYQukdlpRehkt/Q+lVzGxs/mAajxXsSbJ14PV
d/qdUyqCFoyzdDUOa4XObXM2ULn5k2waQUyWzFJeEXEy8q1Tl0wvfAh3wsD8gD+T
qpcIWAVFapMvu1eJOKIIPmk3Sc1uvrwPxN0fXVjK88nGQeJRsR1SUdCDSpRLwfGo
bBrGE1IxVx/tzfSRe0VoQLyj88rtG2i9ZqVVRJRPLl1/9ZTuzLV3io5XoD+lWUH4
rN3OCoxA8JrX4xyifK3yKWMKBQQPXD0wl2gQG1JBbwDJBb7m+sRSC8l+Uvdkkrcb
Fv6DQDBR1Anr2ep7hqAPTk7rWea/Ka+jNvB6xmvljJbch4RciG5Gm9SZ1BWN32Oh
zGJ/5AW50vammkfDcukR2qEwWRYwRnJfOHEFx9sCYVHtW3B7kn1VW1SZA/ox94qH
gs2smWXpwClFCNCFO2PBcdbSIn4wxUYLqIQB6feWV+x4xFk3Nn9hu+fouFkYhA9k
yg+WPGV5ML9xHKGnRRxQq9a0ElkmrRk0bGm7kxglaoI3WFAbdN9icPqpZjhtwgOs
O3VzLbGa5yNg6FbiLakjOpPwlcvZfrNX6xzDBuotxM/qisJCd/hqDPgW5tjj8YDk
nKeIiZ5awDxeJpMYdO5Qm/Xts7Zt0kfLO6ou/oeogFkLoQN52h0=
=H4vg
-----END PGP SIGNATURE-----
