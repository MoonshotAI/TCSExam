-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: xz-utils
Binary: liblzma5, liblzma5-udeb, xz-utils, xzdec, liblzma-dev, liblzma-doc
Architecture: any all
Version: 5.6.1+really5.4.5-1ubuntu0.4
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
 52e6bed09550e62a8e4924118e3bed6e81e55477 33844 xz-utils_5.6.1+really5.4.5-1ubuntu0.4.debian.tar.xz
Checksums-Sha256:
 da9dec6c12cf2ecf269c31ab65b5de18e8e52b96f35d5bcd08c12b43e6878803 1680520 xz-utils_5.6.1+really5.4.5.orig.tar.xz
 b11106c2e0e0898d87cf186d14073770c1ff8999e7c8c4cb02b55bfc0cc8b424 33844 xz-utils_5.6.1+really5.4.5-1ubuntu0.4.debian.tar.xz
Files:
 1d33e0be05c53e7a5641acf5c8b35fdd 1680520 xz-utils_5.6.1+really5.4.5.orig.tar.xz
 95fedbaf29f57b6862dd7def79e09b38 33844 xz-utils_5.6.1+really5.4.5-1ubuntu0.4.debian.tar.xz
Original-Maintainer: Jonathan Nieder <jrnieder@gmail.com>

-----BEGIN PGP SIGNATURE-----

iQJUBAEBCgA+FiEEX6QyiBCwMhrhrX3Dv6T2hRCB8x0FAmrJQX8gHHNoYWZheWF0
Lm1hanVtZGVyQGNhbm9uaWNhbC5jb20ACgkQv6T2hRCB8x0O4RAA4HPn0qjSAPEx
WdjWQMyUn5QPld29J0ljCAttEGDPtlsc+91wCc8z9CV4wwloOxdR6ug5Jifwr6/T
RFtJIMGKnqUVkYhPe+U3s2Rp7s0w9+7y0n8G+K6JH0eMdfyCoF9zpYk6O5EieY9l
0dSNDds9NFqb1F97TzRi9Y3CI/p66C35POr9LlJ/g3GBiO/5Uw358OBVFtnFr3oV
U1HJ3aJ4ey1MJV6htE03d107F4kXo3MhnVviB5k6KfRmjY1gVDgrNtPwDiDKcjtB
ywK0keOgFeTL9JbgoPNV7q/iDiKaU6gu57V8McsqHqKx4eiVzz6KWHAqyFH5Rc9b
Bi2CGtPHoDVD16b8WDNMh49nwalUxUd1yw0XY2Sjp6rCqv05BC1wjCWP9byCi4P2
KOuPwqNMGoPfiewaZDRfK3CpOEvBch0k4MlaqDBlL3jYbAAKjyMIcSYht8uRBVVd
nCiqd0HKujc1O32ffiEhLVRqilrCbQ7GA/BUZAij3RwaAe53p+w3dhfKgvPMBLb6
uCLsupGoYASFFG3ME+jUe3hkcxP4XlVRdzj+s/5SU8fqyW7ax9gVNZK9W246bcAc
RcKWqREbxq8JIvB9jByMtrr6Y+KUjaXgACUiYOkJ8mIGA7+uBTBeyYYp4SvdFbU7
av3FSeEIFyU7QdxuLFULUzWGW96bAM4=
=RrpM
-----END PGP SIGNATURE-----
