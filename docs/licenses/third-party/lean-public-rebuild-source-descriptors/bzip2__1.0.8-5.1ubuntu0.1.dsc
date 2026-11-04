-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: bzip2
Binary: libbz2-1.0, libbz2-dev, bzip2, bzip2-doc
Architecture: any all
Version: 1.0.8-5.1ubuntu0.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Santiago Ruano Rincón <santiago@debian.org>, Anthony Fok <foka@debian.org>
Homepage: https://sourceware.org/bzip2/
Standards-Version: 4.6.0
Vcs-Browser: https://salsa.debian.org/debian/bzip2
Vcs-Git: https://salsa.debian.org/debian/bzip2.git
Testsuite: autopkgtest
Testsuite-Triggers: @builddeps@, build-essential
Build-Depends: debhelper-compat (= 13)
Build-Depends-Indep: texinfo, docbook-xml, docbook2x, xsltproc
Package-List:
 bzip2 deb utils standard arch=any
 bzip2-doc deb doc optional arch=all
 libbz2-1.0 deb libs important arch=any
 libbz2-dev deb libdevel optional arch=any
Checksums-Sha1:
 bf7badf7e248e0ecf465d33c2f5aeec774209227 810029 bzip2_1.0.8.orig.tar.gz
 aa6de67fbe4ff03f7a235b437e1458f890c88668 27529 bzip2_1.0.8-5.1ubuntu0.1.debian.tar.bz2
Checksums-Sha256:
 ab5a03176ee106d3f0fa90e381da478ddae405918153cca248e682cd0c4a2269 810029 bzip2_1.0.8.orig.tar.gz
 77c61e0490ff7cf49aa8ffe62e117e85b3af08e14341c4b851f8d7ec757fe099 27529 bzip2_1.0.8-5.1ubuntu0.1.debian.tar.bz2
Files:
 67e051268d0c475ea773822f7500d0e5 810029 bzip2_1.0.8.orig.tar.gz
 3bc2c06d0004a74bec0c244af4f6ac24 27529 bzip2_1.0.8-5.1ubuntu0.1.debian.tar.bz2
Original-Maintainer: Anibal Monsalve Salazar <anibal@debian.org>

-----BEGIN PGP SIGNATURE-----

iHUEARYKAB0WIQSyA9nA4R5iZYAVzFrgLM9xllPy5AUCao/PggAKCRDgLM9xllPy
5KMoAPwN/hXj+lXaccI1WA2tImmFkMbx9+y5eL2SVMBLU3qBXwEA5jQtOCDPeRP/
oYUA4w9woDtoaWPaclWysw3c1XVNzgs=
=Sm/5
-----END PGP SIGNATURE-----
