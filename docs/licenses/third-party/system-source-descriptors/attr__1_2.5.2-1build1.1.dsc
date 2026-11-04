-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: attr
Binary: attr, libattr1-dev, libattr1, attr-udeb, libattr1-udeb
Architecture: any
Version: 1:2.5.2-1build1.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Homepage: https://savannah.nongnu.org/projects/attr/
Standards-Version: 4.6.2
Vcs-Browser: https://git.hadrons.org/cgit/debian/pkgs/attr.git
Vcs-Git: https://git.hadrons.org/git/debian/pkgs/attr.git
Testsuite: autopkgtest
Testsuite-Triggers: autoconf, automake, autopoint, build-essential, libtool
Build-Depends: debhelper-compat (= 13), debhelper (>= 13.10), autoconf, automake, gettext, libtool
Package-List:
 attr deb utils optional arch=any
 attr-udeb udeb debian-installer optional arch=any profile=!noudeb
 libattr1 deb libs optional arch=any
 libattr1-dev deb libdevel optional arch=any
 libattr1-udeb udeb debian-installer optional arch=any profile=!noudeb
Checksums-Sha1:
 dfced877779583861401389eea82dfeb88cb5d3a 334180 attr_2.5.2.orig.tar.xz
 eee0e22675431900d88d16eab9d76c122cffb89e 833 attr_2.5.2.orig.tar.xz.asc
 76ce5cc9805f72b8c7cda10b894335a35713a483 26032 attr_2.5.2-1build1.1.debian.tar.xz
Checksums-Sha256:
 f2e97b0ab7ce293681ab701915766190d607a1dba7fae8a718138150b700a70b 334180 attr_2.5.2.orig.tar.xz
 eeac729088d3c6379e91b7596cb3582e46b047c47f0fa3c5c77f9c9e84dc3a4c 833 attr_2.5.2.orig.tar.xz.asc
 9d020c0d557c8a932da9e330683e2cfaa8afc932bd9181b96dfda23077901e7f 26032 attr_2.5.2-1build1.1.debian.tar.xz
Files:
 4da9c1d25394946434e5913f49d778b6 334180 attr_2.5.2.orig.tar.xz
 52351f08e9562bc6af1dd6010d6a96d1 833 attr_2.5.2.orig.tar.xz.asc
 d12ec225c4ea232e39eda8eece0753bf 26032 attr_2.5.2-1build1.1.debian.tar.xz
Original-Maintainer: Guillem Jover <guillem@debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEVovyKmYzfL/Jprm3LIPbyOm9DjcFAmb+IaYACgkQLIPbyOm9
DjeLjBAAlXRqNH+FK0VHclFzVFCPGP+t48p1elwQHpY8QfFWAsPmuX/Oy1vIeg5F
7P2uW0CDHxw1/cdyGiq2r/drudc1MkE4f6gcHjLdZ3thUBSgknwjUMr2fK5UrmB2
R5aBrYlVA/vqKLA4v3dnFtLkhA3LyFv5HJ+ap9uut0fCYKO58PPJAiUTSkfurzj/
a8pCagWnFRA4Fhvj4wWeaTESXC/l/2nhyTBpk1/NbSM/ahn/83NKJOfPk6DooV/A
ATiiI1vgL71tbQh8AxgD//FdrOiKQn4mVp3hfbzB3blHS1m6Xiy2w9CMHSM1kdTK
9ytbVb1X2dnrMkJ+BusXyVvfbPOP7fzTTKA1EQUyq02xuG/Mr8GOdi+9lKtvYLy6
dlpV83D3Ids3OfzS+zEQwhN+7zNxQfDFifJR9jei+U3HQswZu7ExYONBmhT6wca5
izSLtxFsrwuM2F9a19h2vbzQF+jPzYVwVaqPRMhYzDs8sTFxwWoWRTLrr/k20NqP
7TADPSoDJrqGQSL+jXlai70iPQqmT54RB0tWU/+IpSMvpYoqgtmEFuWe4I9Ayllb
LhjdKdHe+g+/mVkmrMDcI9PPKEUHTC77N2Epn875fsvi860qJFUGfsro/yTl2s0/
4HvVDpu0HDX81q0E4PUpm/7fzcV9rW+adnG/LpWeOXPcRSay0n0=
=y/l6
-----END PGP SIGNATURE-----
