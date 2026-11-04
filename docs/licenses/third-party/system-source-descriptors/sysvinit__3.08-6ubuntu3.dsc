-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: sysvinit
Binary: sysvinit-core, sysvinit-utils, sysv-rc, initscripts, bootlogd
Architecture: any all
Version: 3.08-6ubuntu3
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders:  Ian Jackson <ijackson@chiark.greenend.org.uk>, Benda Xu <heroxbd@gentoo.org>, Adam Borowski <kilobyte@angband.pl>, Vincenzo (KatolaZ) Nicosia <katolaz@freaknet.org>, Mark Hindley <leepen@debian.org>,
Homepage: https://github.com/slicer69/sysvinit
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/sysvinit
Vcs-Git: https://salsa.debian.org/debian/sysvinit.git
Build-Depends: debhelper-compat (= 13), libselinux1-dev [linux-any], po-debconf, po4a
Package-List:
 bootlogd deb admin optional arch=any
 initscripts deb admin optional arch=all
 sysv-rc deb admin optional arch=all
 sysvinit-core deb admin optional arch=any
 sysvinit-utils deb admin required arch=any essential=yes
Checksums-Sha1:
 40e900162f664c6c4210b6ed2bc432db3fc86ad3 513674 sysvinit_3.08.orig.tar.gz
 31faa9f32ecbb91a1993627a6f6ac26f8c43901d 140128 sysvinit_3.08-6ubuntu3.debian.tar.xz
Checksums-Sha256:
 325e42ae4ae5ae3e4d989e0604aeb5e4eae5f3ee21e401db3c79000718f8c836 513674 sysvinit_3.08.orig.tar.gz
 1a8a8365cdc393e349fc115094a8ef7c52082ed22e7f1337ab1b8dd6b5e0103b 140128 sysvinit_3.08-6ubuntu3.debian.tar.xz
Files:
 701cc7ae142c520593bd9f2c9bdf833f 513674 sysvinit_3.08.orig.tar.gz
 b8ff687376e43f3ca9221eeafa4c6af9 140128 sysvinit_3.08-6ubuntu3.debian.tar.xz
Original-Maintainer: Debian sysvinit maintainers <debian-init-diversity@chiark.greenend.org.uk>

-----BEGIN PGP SIGNATURE-----

iQJHBAEBCgAxFiEET7WIqEwt3nmnTHeHb6RY3R2wP3EFAmYUGYgTHGp1bGlhbmtA
dWJ1bnR1LmNvbQAKCRBvpFjdHbA/cdiSEACQQiw1oHjtds9w52pPxFxaF55Kvs6G
29CIbGSvJU1D//J/JOcmXiSU+Ml84IiRfCQzXud43ak4X9rQtVddthTDX5LIFfwc
/7lRRILxjBQPMTp/EDT71owRTu3M7gd3N8TVsOyBgGk75s0pR6ebzuu2E8HaKcDw
54DTzXELx2Fvh/81HQUfiVTM+YgEnmeCoD8F9VXAqmnmbgNE7epH/7dowUtU3SPF
l3PLVCR1G1fvoJ0FvKjHpUt5ShtXpjQPNOEW70X+hq09+gQGflTodRigjSz2CWQD
8EwkZBQ5/QBO+PRxaYqYknifkHPl5QYtI9JQ3OTdmDwswpzMxKQvvM6Km4DBxKp3
6iuI8B+cJb4+Km1QmrsYXy0F6hfxUF3TpPRg4jAIdSa/agOnQ/NG4x9bPqhrTXGe
/3kq+qf9PWCFapPHverwW+qQ2LBna95faT3fUudf9yqBCy64stDsGpdDj7RpT7a0
HK7AyL19GJHySN87K3CXayobodp8aPspnrKNlMjWBTiPs/hf3mpyxgxujykVbwau
UBizARdQwlYT5mP0KnX7G6Px5vIZJipN5n4N+/oXfgwCcEFvOxnmM5+K+FHJggFf
ZXtE+J4JggzhdViWeQtZXihdcyLFTnoxH2ZYW+0PzHEmJU+CBKaTamzmZh0h5Bwd
uJxZdpONPrtGrQ==
=7Cpw
-----END PGP SIGNATURE-----
