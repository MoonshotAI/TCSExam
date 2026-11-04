-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: acl
Binary: acl, libacl1-dev, libacl1, acl-udeb, libacl1-udeb
Architecture: any
Version: 2.3.2-1build1.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Homepage: https://savannah.nongnu.org/projects/acl/
Standards-Version: 4.6.2
Vcs-Browser: https://git.hadrons.org/cgit/debian/pkgs/acl.git
Vcs-Git: https://git.hadrons.org/git/debian/pkgs/acl.git
Testsuite: autopkgtest
Testsuite-Triggers: autoconf, automake, autopoint, build-essential, libattr1-dev, libtool, pkgconf
Build-Depends: debhelper-compat (= 13), debhelper (>= 13.10), autoconf, automake, gettext, libtool, libattr1-dev (>= 1:2.4.46-8)
Package-List:
 acl deb utils optional arch=any
 acl-udeb udeb debian-installer optional arch=any profile=!noudeb
 libacl1 deb libs optional arch=any
 libacl1-dev deb libdevel optional arch=any
 libacl1-udeb udeb debian-installer optional arch=any profile=!noudeb
Checksums-Sha1:
 2674394a4061791c77d80fd2089a39c3675a5980 371680 acl_2.3.2.orig.tar.xz
 884c1cae6bbc52db9deba2f5523f6624df796201 833 acl_2.3.2.orig.tar.xz.asc
 91fe98c9c0c5b7e0677ff95be264cadc3d6e6aee 23472 acl_2.3.2-1build1.1.debian.tar.xz
Checksums-Sha256:
 97203a72cae99ab89a067fe2210c1cbf052bc492b479eca7d226d9830883b0bd 371680 acl_2.3.2.orig.tar.xz
 184c6a903490885a096095db67b433a04542c6569f167cbe8115268c0f227273 833 acl_2.3.2.orig.tar.xz.asc
 0d324adb403a50aa2889a11e098d34ce5adecd1cb89f83799f66dbb1d8b71280 23472 acl_2.3.2-1build1.1.debian.tar.xz
Files:
 590765dee95907dbc3c856f7255bd669 371680 acl_2.3.2.orig.tar.xz
 ea6ee7f69d122317eabf7641aeb083ff 833 acl_2.3.2.orig.tar.xz.asc
 3c5017867ebbd36e8cc7761d0daf4b7b 23472 acl_2.3.2-1build1.1.debian.tar.xz
Original-Maintainer: Guillem Jover <guillem@debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEVovyKmYzfL/Jprm3LIPbyOm9DjcFAmb+IeAACgkQLIPbyOm9
DjcobA//dmD5P/nXGm0BJV88Y3TCsHPUVHRZQTh4nKoueJ/30bD5At07xu2xULmC
LzYSMwPmLdSwtC0WzlHocxADFSdAAlp7XIaqFD421j7c368qS6NChJw92ZqZie0K
esBXMP1/yVwNkBym9u18DbdRwsQcMFWMHiFkV4m/ncFLxC6wPAHp/cOZJZVEUCK+
kNWDMXiyTXAr/fYf5vWuXhNZPv/A6nS5CsikKNK7gEMwo7SOa/bfGe7KTqtWmbHa
THSVT35IPFHX0pf9dTTr2kacLOxAV3yzUUvNXK093lEd9VkXw9UKNBDQU+FDhNhV
vXvYKVCvHOfLCprElv5CD6yIU7nrMLHyVv8WViicFY2oZ6KUQmZLSgBGVlvOt2n+
HDm8AXJoNQ2cFwPCYtPiHYR9QKpzjxfy0k1+HRM0m08LIyisXZR4fvWSBViuXKn9
WM+o46HAtGKBERazrZSDYzp9ibB2ezrnOPjxhgmOVVvdh8whTlvlYS8T55PeHL87
yXrUQCBmbUR38lV2ncQg04hXrV7cDGciUpqnLeWnqt7gaxdtPSTlWzPTuZsjJPw0
LQtY/IcosdC0WfHq3a4DOtTt3ikr5oocCnqCXX0TkdOn6QA5FRAsuuIYsm+EMwdq
DvwSxdOjkcwdDxHB44013DhxhGrfiDQ1GAxyTxfVI9+oLfYH5CQ=
=Cnrt
-----END PGP SIGNATURE-----
