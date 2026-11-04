-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: e2fsprogs
Binary: fuse2fs, logsave, e2fsck-static, e2fsprogs-l10n, libcom-err2, comerr-dev, libss2, ss-dev, e2fsprogs-udeb, libext2fs2t64, libext2fs-dev, e2fsprogs
Architecture: any all
Version: 1.47.0-2.4~exp1ubuntu4.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Homepage: http://e2fsprogs.sourceforge.net
Standards-Version: 4.6.2
Vcs-Browser: https://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git
Vcs-Git: https://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git -b debian/master
Testsuite: autopkgtest
Testsuite-Triggers: fuse3
Build-Depends: dpkg-dev (>= 1.22.5), gettext, texinfo, pkg-config, libfuse-dev [linux-any kfreebsd-any] <!pkg.e2fsprogs.no-fuse2fs>, debhelper-compat (= 12), dh-exec, libblkid-dev, uuid-dev, m4, udev [linux-any], systemd [linux-any], systemd-dev [linux-any], cron [linux-any], dh-sequence-movetousr
Package-List:
 comerr-dev deb libdevel optional arch=any
 e2fsck-static deb admin optional arch=any profile=!pkg.e2fsprogs.no-static
 e2fsprogs deb admin required arch=any
 e2fsprogs-l10n deb localization optional arch=all
 e2fsprogs-udeb udeb debian-installer optional arch=any profile=!noudeb
 fuse2fs deb admin optional arch=linux-any,kfreebsd-any profile=!pkg.e2fsprogs.no-fuse2fs
 libcom-err2 deb libs optional arch=any
 libext2fs-dev deb libdevel optional arch=any
 libext2fs2t64 deb libs optional arch=any
 libss2 deb libs optional arch=any
 logsave deb admin optional arch=any
 ss-dev deb libdevel optional arch=any
Checksums-Sha1:
 987645f563f279ab32aac19d824c64e9690e3152 9637717 e2fsprogs_1.47.0.orig.tar.gz
 e556795d4fe3ba739219658fd104189ca08a8db2 488 e2fsprogs_1.47.0.orig.tar.gz.asc
 18af97488479380a10d94a88055a848089e0abf8 90580 e2fsprogs_1.47.0-2.4~exp1ubuntu4.1.debian.tar.xz
Checksums-Sha256:
 6667afde56eef0c6af26684974400e4d2288ea49e9441bf5e6229195d51a3578 9637717 e2fsprogs_1.47.0.orig.tar.gz
 704928204a52ddaa0ac8ef549c1bfba3c38e66c361d3853c8a4c38e6082b90f1 488 e2fsprogs_1.47.0.orig.tar.gz.asc
 26b381ec175ff52d1cc2fd1b217f84b9e1d7d33a58dcbaf8942115dd27a03f84 90580 e2fsprogs_1.47.0-2.4~exp1ubuntu4.1.debian.tar.xz
Files:
 6b4f18a33873623041857b4963641ee9 9637717 e2fsprogs_1.47.0.orig.tar.gz
 0d285d11f13417932bc475cb6ae27af2 488 e2fsprogs_1.47.0.orig.tar.gz.asc
 0b7e85930490f16d57c81d0c3df7278a 90580 e2fsprogs_1.47.0-2.4~exp1ubuntu4.1.debian.tar.xz
Original-Maintainer: Theodore Y. Ts'o <tytso@mit.edu>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEE4qlMxBx1Pex4dJYuxTfgBIBe5lcFAmaZVSAACgkQxTfgBIBe
5lddRhAAhWzYMyzX64ZQ6urnvBjXU46vt85XFr+ugRHIByd1X6/2ZJ/2+logzllY
F72gO5nYVE3BlsiJ41WW+lgPYVRKDs3Q3yo1Gw9UZUSJ+A4VeYPAM4A/000T1ly/
7u5nIvkrtB3gXczqpuWjRC2o/R0lMR5qwRPVUcPeRlEFc7fiQ10eci9ux9qoeD2r
vAdDB3dx5qRCqwNYc6aeD5Ir1/GmEPsBrpnHnp5dy8i6c8x4XkA76B7l3r6f/bOt
Hj2q+AuAsWUEUPK5tHeMNFhJd7/BWQEEkyCYo/4+ALPjCTEWyXWPG9/8t6i++f1z
3QpI9Fu0mdYMeBqbJFxW9geB1IyRHRn3kdaephSkUS4x9O4wVwIo57eGrN9P/1o3
y9feCUfhNg6YD4JMG20uiqfMl/Qus8rhxkx9tjrE9PRxaj7JmT2MJXFlfGZ2qDie
JrJa7YY18BOhA1cy9ZuZCCi6PAa6u7ihkSaMPLWv4ig9OFYReg0vMtG00GkMvFGV
55pcDRYaaL+t1PiBHFT+DuKfYIycZFR4qJFjbvgJzZfQHg2fx/jbtXyQYqE78LKQ
AZE9TrSgEkQXqbyeOCWjjxEGAlR3iYMGiMGcS2KALzKG5QImbG3YTpGmtaXPeJZ8
mLKo8DLX4CDdDucjorCh7Cb0CiPnLglEsmtYrbCdT2IE7IMNWnU=
=2txQ
-----END PGP SIGNATURE-----
