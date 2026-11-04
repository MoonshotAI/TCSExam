-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: brotli
Binary: python3-brotli, brotli, libbrotli-dev, libbrotli1
Architecture: any
Version: 1.1.0-2build2
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
 f630bb45f952c653df9f5f24201d69d5221681c7 5644 brotli_1.1.0-2build2.debian.tar.xz
Checksums-Sha256:
 10973f4b4199eafa1d5735ef661ddb2ec2f97319ee9fd1824d4aabe08cff5265 512036 brotli_1.1.0.orig.tar.gz
 96603222d7b6edb3253a846852972b6bde5b86814907d5540249e6950980a943 5644 brotli_1.1.0-2build2.debian.tar.xz
Files:
 97d4c95fcb7d5d6131c8d5a07eaa7d4b 512036 brotli_1.1.0.orig.tar.gz
 07cb1c9a430dd846d7c5463c5be15442 5644 brotli_1.1.0-2build2.debian.tar.xz
Original-Maintainer: Tomasz Buchert <tomasz@debian.org>

-----BEGIN PGP SIGNATURE-----

iQJOBAEBCgA4FiEErEg/aN5yj0PyIC/KVo0w8yGyEz0FAmYJEMMaHHN0ZXZlLmxh
bmdhc2VrQHVidW50dS5jb20ACgkQVo0w8yGyEz3aABAAziVBYCqcPUId/w+s+yWv
94vXgw2Sco7WSUnIXymiC5na1MRGCP/KyClJPNQtIXrCxlydnflGK8ijClJcXEao
o14lBhGxfG9qxvLlvJdQJF2DPqhZcKK1l632UmxJ7Gd0OYQwUHO4IjT+tsvPKtgd
ou/HEqElXH2/86ivsP/6uOgid7xfZN9m3XdMfHkj8Ic2L6hywynyHWjo4eOEf4vV
cHh9HWP5cRwiA8xz6FDNYIWUgvpMdGRhUyafVfHbIJ0qbG2S8CvStnfjscfTwR+L
VjSn+jVpSeRTld9FJptRCOKDe1VBksSYGYUz6umEpKCMshpZfzCKA7seISAQnvOK
1Xxexxqbc0nCbqp1bOFBFQjxZoRhX8D7XlQjU333hIv/fREL1hOweU0bvVJpJe+w
3Skpm8vsdenMjMs5m2+v7vfePD4ma8FwPQjHJ6jCWBAPkzMFNqVg0WRlZkq3s+3o
1kkk/nBfh19M/ooByHrDZvw4tksEXp/edKzYnYaCHy83FUEPfPrgZB05vt4LimQz
wSTCXUCq3aEfoSnqiLDqppE8gjfsJ+NL5oMyTKzEVPYyyB+edJ5GdcB+kMl3WvCD
zEjW47cnuqL4NbBOJmFk4sspMO+gN6kpHIWRdqdnjR/wmZVU41c/yjpcv6xeWyJW
5/461BHIEe6TZwFEp+yihuo=
=AFkY
-----END PGP SIGNATURE-----
