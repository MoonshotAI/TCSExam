-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: libcap2
Binary: libcap2-bin, libcap2, libcap-dev, libpam-cap, libcap2-udeb
Architecture: linux-any
Version: 1:2.66-5ubuntu2.4
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Homepage: https://sites.google.com/site/fullycapable/
Standards-Version: 4.6.1
Vcs-Browser: https://salsa.debian.org/debian/libcap2
Vcs-Git: https://salsa.debian.org/debian/libcap2.git
Testsuite: autopkgtest
Testsuite-Triggers: gcc, libc-dev
Build-Depends: chrpath, debhelper-compat (= 13), gperf (>= 3.1), indent, libpam0g-dev
Package-List:
 libcap-dev deb libdevel optional arch=linux-any
 libcap2 deb libs optional arch=linux-any
 libcap2-bin deb utils important arch=linux-any
 libcap2-udeb udeb debian-installer optional arch=linux-any profile=!noudeb
 libpam-cap deb admin optional arch=linux-any
Checksums-Sha1:
 d440e60686bd542e2a6481986c63ee8de625563e 181592 libcap2_2.66.orig.tar.xz
 5dec9cd9fae3dad95729242ef07a44cf8e0535c8 24724 libcap2_2.66-5ubuntu2.4.debian.tar.xz
Checksums-Sha256:
 15c40ededb3003d70a283fe587a36b7d19c8b3b554e33f86129c059a4bb466b2 181592 libcap2_2.66.orig.tar.xz
 7eb46752c6b59984494d2f641a049b9d4b394b7d1fe067729ccbc413c5943136 24724 libcap2_2.66-5ubuntu2.4.debian.tar.xz
Files:
 00afd6e13bc94b2543b1a70770bdb41f 181592 libcap2_2.66.orig.tar.xz
 5fd805d3708f6c707c8c1caed432f7dc 24724 libcap2_2.66-5ubuntu2.4.debian.tar.xz
Original-Maintainer: Christian Kastner <ckk@debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmnX0oQACgkQZWnYVadE
vpMIkRAAnPYOCExoWOoKyoRdrwF7zKiCusB8Gr+z8pIZwcO/LiLwJum6qKrOzcX6
Yh39wkIbLfzSAVTBut5s1W7Agm7hIVCe3odgCRGloqde5niIsqxPAe3yO2Ntmz92
gW4qy3CgYWT08NOZe7LB8pvx1AQnuu6gD+r/CIiq6rXSDYK0AmVVYFsVqbEEq2vF
17dJ8QjhBm5896oCCPVXyGDvzbff7F06Wkcc3zN+UPbJ+wuFsMhm1fUuoEt546yS
NTfqxSs1ua4ayMgW8pb0NDB6OxuadGz4/YsM+GrGcqn10KMkB/SGH99KDdyntLym
Z8VmkXgmf7qRGjFpdnIdjVwWD/bvEnw9px4GsBFd05iVwMWUBNslIfV9+StO3YHr
GMc3XSEWlmWXlWD4f2q8aVFpFVSIQe6hrJxJN9IqSn5yxz/90TAAGAEtAxHSI+x6
4CRa8Zc2HnXiIF0wPMv9NP89hEgl2fIqEYEszmrWOMWro+o5mMiLMgaMvZ9Yrcpq
OjLePpA/+ULUaMd7sfHTs6bZuqa2bkop+7X/uxcKKdhhY7ElPKbS+lS8KOK/cvHT
9v8OiyYm/TPYZCbKQajPl4W4kPOYyytwNq9IXCcNR7lR1FB2NEz/xMcaOPBjc+0X
yazmfyHxj3LBlh/F7PiR6384HpLEGU+DxdrVRcBb89qWhE//9uo=
=ySTl
-----END PGP SIGNATURE-----
