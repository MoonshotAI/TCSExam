-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: brotli
Binary: python3-brotli, brotli, libbrotli-dev, libbrotli1
Architecture: any
Version: 1.1.0-2ubuntu0.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Ondřej Surý <ondrej@debian.org>
Homepage: https://github.com/google/brotli
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/brotli
Vcs-Git: https://salsa.debian.org/debian/brotli.git
Testsuite: autopkgtest
Testsuite-Triggers: python3-all
Build-Depends: cmake, debhelper (>= 13), debhelper-compat (= 13), dh-python <!nopython>, libpython3-all-dev <!nopython>, python3-all-dev:any <!nopython>, python3-setuptools <!nopython>, python3:any <!nopython>
Package-List:
 brotli deb utils optional arch=any
 libbrotli-dev deb libdevel optional arch=any
 libbrotli1 deb libs optional arch=any
 python3-brotli deb python optional arch=any profile=!nopython
Checksums-Sha1:
 c1a06bd9cb912a8b5f07b2bd504af78ec6d0335c 512036 brotli_1.1.0.orig.tar.gz
 4cc4c611cfb33f2489378997858937e76b11470e 7892 brotli_1.1.0-2ubuntu0.1.debian.tar.xz
Checksums-Sha256:
 10973f4b4199eafa1d5735ef661ddb2ec2f97319ee9fd1824d4aabe08cff5265 512036 brotli_1.1.0.orig.tar.gz
 744230cae71f1ba9fbef6b897195393dca0f94641b286a3a183898fe6a77ef59 7892 brotli_1.1.0-2ubuntu0.1.debian.tar.xz
Files:
 97d4c95fcb7d5d6131c8d5a07eaa7d4b 512036 brotli_1.1.0.orig.tar.gz
 8c4be5c54f62bf58b0f3193550265d2e 7892 brotli_1.1.0-2ubuntu0.1.debian.tar.xz
Original-Maintainer: Tomasz Buchert <tomasz@debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmreUdkACgkQZWnYVadE
vpMhZg/+IZM5lVjwtL47/I4dy5pDEnhGwcM/qLEpbXHQUZWob44OLp/K4gbdAlVc
/PdEXMEIojnjJm/BwKWNZnPFxcfv9x4yLJGQj8arFpibZEXUw+n/3XmeZdbF5Aoy
Fqa/eHL5rpQRGZtSZMtqyq6cpad/meSInBqRbTGL7uUhZ5AV8/CNag+vrRJ0ZGi5
GBuU3QC/PhC4HDMe925Pj5nuTYbXRL9jPij6o/BTtxRZsWkWbgkUdWNTLSGd/Wyv
52oXxV1bYsnajAB5nj/q3yCb14XQNgwXo4z4K24RZTMnb8RaYq6TLay3xa0GD76W
2k3+2c29BzukhADSCSURbs3jWLG1tWk5L4u3z4xFg+Aorn87aPiPz3q8fpinEGcB
w23VsOhSh87lEb9qpGmKOqkhhUyZxlgANBrgw4JvSz/IgGIgGlAkJ3k9kxoAJx4M
qiRb/y9a/8KhDyxLlzjQaNS/K242ZtE4JXEAxUVmShJyuQpZCkWF/6ET6KoqEZSD
DRRCxZt36ykgOcdHl1knFIjPL2wXknEnLkRhRf+FZg3XHdGeQZOZ+WYpTYMFALXg
r04mDTj4ST4xmGuAWXe0RCPdMtYoUaMZYv3rJ9MrSUgS5N5LmpAcvfB0jlo+G4gz
UsHl+Dql3SfmDZpCQFqEq7GO7D8lhIISo5BymXaGRyF1FGahVi8=
=uBma
-----END PGP SIGNATURE-----
