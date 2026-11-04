-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA256

Format: 3.0 (quilt)
Source: gnupg2
Binary: gpgconf, gnupg-agent, gpg-agent, gpg-wks-server, gpg-wks-client, scdaemon, gpgsm, gpg, gnupg, gnupg2, gpgv, dirmngr, keyboxd, gpgv-udeb, gpgv-static, gpgv-win32, gnupg-l10n, gnupg-utils
Architecture: any all
Version: 2.4.4-2ubuntu17.4
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders:  Eric Dorland <eric@debian.org>, Daniel Kahn Gillmor <dkg@fifthhorseman.net>,
Homepage: https://www.gnupg.org/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/gnupg2
Vcs-Git: https://salsa.debian.org/debian/gnupg2.git -b debian/main
Testsuite: autopkgtest
Testsuite-Triggers: debian-archive-keyring, gnupg1
Build-Depends: automake, autopoint, debhelper-compat (= 13), file, gettext, gpgrt-tools, libassuan-dev (>= 2.5.0), libbz2-dev, libgcrypt20-dev (>= 1.9.1), libgnutls28-dev (>= 3.2), libgpg-error-dev (>= 1.46), libksba-dev (>= 1.6.3), libldap2-dev, libnpth0-dev (>= 1.2), libreadline-dev, libsqlite3-dev, libusb-1.0-0-dev [!hurd-any], openssh-client <!nocheck>, pkg-config, texinfo, zlib1g-dev | libz-dev
Build-Depends-Indep: binutils-multiarch [!amd64 !i386], libassuan-mingw-w64-dev (>= 2.5.0), libgcrypt-mingw-w64-dev (>= 1.9.1), libgpg-error-mingw-w64-dev (>= 1.46), libksba-mingw-w64-dev (>= 1.6.3), libnpth-mingw-w64-dev (>= 1.2), libz-mingw-w64-dev, mingw-w64
Package-List:
 dirmngr deb utils optional arch=any
 gnupg deb utils optional arch=all
 gnupg-agent deb oldlibs optional arch=all
 gnupg-l10n deb localization optional arch=all
 gnupg-utils deb utils optional arch=any
 gnupg2 deb oldlibs optional arch=all
 gpg deb utils optional arch=any
 gpg-agent deb utils optional arch=any
 gpg-wks-client deb utils optional arch=amd64,arm64,armhf,ppc64el,riscv64,s390x
 gpg-wks-server deb utils optional arch=amd64,arm64,armhf,ppc64el,riscv64,s390x
 gpgconf deb utils optional arch=any
 gpgsm deb utils optional arch=any
 gpgv deb utils important arch=any
 gpgv-static deb utils optional arch=any
 gpgv-udeb udeb debian-installer optional arch=any profile=!noudeb
 gpgv-win32 deb utils optional arch=all
 keyboxd deb utils optional arch=any
 scdaemon deb utils optional arch=any
Checksums-Sha1:
 228b3984325fdeebc5e3f2d165c6419a5ebc28de 7886036 gnupg2_2.4.4.orig.tar.bz2
 d75fe015dfc85bab42825fed012915a702f9e98f 386 gnupg2_2.4.4.orig.tar.bz2.asc
 f1ed4475b993d9c0c5e781c91303083b1a1f4caa 97376 gnupg2_2.4.4-2ubuntu17.4.debian.tar.xz
Checksums-Sha256:
 67ebe016ca90fa7688ce67a387ebd82c6261e95897db7b23df24ff335be85bc6 7886036 gnupg2_2.4.4.orig.tar.bz2
 47986167998b2cb6be4e4cdeef0c468139e06580ed65ce2cf241c527d74e54db 386 gnupg2_2.4.4.orig.tar.bz2.asc
 234250d6e9288ddb8e481f2da515ffa2bb384be0d9edd818487a82f15e8f307c 97376 gnupg2_2.4.4-2ubuntu17.4.debian.tar.xz
Files:
 114ac6367668a330ffae1ade6d79133a 7886036 gnupg2_2.4.4.orig.tar.bz2
 5939daa78b03ca16bd8497cf4d3f5f2a 386 gnupg2_2.4.4.orig.tar.bz2.asc
 ae6624726f4e68918912f6f1ca13ba49 97376 gnupg2_2.4.4-2ubuntu17.4.debian.tar.xz
Original-Maintainer: Debian GnuPG Maintainers <pkg-gnupg-maint@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQJOBAEBCAA4FiEEhC9y9XdAFQPCvYXchGmXSGiknnUFAmldR8YaHGFsbGVuLmh1
YW5nQGNhbm9uaWNhbC5jb20ACgkQhGmXSGiknnWMVw//Z9il6qiHu8nlaC/gPMKO
S3H+9WRbEhsgr1DYjZ3GMO8QPrQRfdnbJ0LvFRs6WMGfDAT2nfw4blHNDkJdmRZN
J5fAy5jw8y2VJUV5U5KrqrZQDOMj2iASjYfFvA1C5xt7HnBZ6KnSHai2RjT5+OQ4
W0mQ2h1t7Q0HsyWQP6vbsYaMvBLghRkDDk3b6yLJkKDoH8iFocT04sMK7mW7p0xn
rpZdQhJ/h2kbvivuP4TJ7Lk3o8/i73QWCHR7tVqpZxV1WP6RPHL5e/ATBWsQD34n
EfI8qKCmJR/nDJyQHKdChLeDd3jcPBmLrAesG+94TRAbHqz98v7vSDGLejJjVfsz
KbMPjK+gE3EwVoBwVz58QcbNDcfybBp2b+bE5ugi1Fd/RcRlQTGgqBW9pqR/m6P1
+mgELD7flxcJj+67+sWfJ+LKFmz45Qs5NpAUgw6yodq4ciyfIjmjyfXu+6AZSKej
l56Fp85ZvEjFD/m2wWOB0IlnkC0g46+2/SodcwlYMOUYsWlO9R4X/BBmEemeOYFv
DIblSqIS78yHWu4bW3wMLmRKTffSQlnpWX8YaqvQOu57ozx5swqov8xXyQpSjGVC
UayaJYDqJdTSFJGO5uJBiQt7FtEgnTw9pquVGhd10jCYMEXBTuHuFoEt7zU5RDA9
s4giJ1FV0XBkDMEAnCpHjlw=
=oPt7
-----END PGP SIGNATURE-----
