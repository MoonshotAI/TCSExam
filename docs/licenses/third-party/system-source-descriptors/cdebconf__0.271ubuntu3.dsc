-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (native)
Source: cdebconf
Binary: cdebconf, cdebconf-gtk, libdebconfclient0, libdebconfclient0-dev, cdebconf-udeb, cdebconf-priority, libdebconfclient0-udeb, cdebconf-text-udeb, cdebconf-newt-udeb, cdebconf-gtk-udeb
Architecture: any all
Version: 0.271ubuntu3
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders:  Colin Watson <cjwatson@debian.org>, Cyril Brulebois <kibi@debian.org>
Standards-Version: 3.9.7
Vcs-Browser: https://salsa.debian.org/installer-team/cdebconf
Vcs-Git: https://salsa.debian.org/installer-team/cdebconf.git
Build-Depends: debhelper-compat (= 13), po-debconf, libslang2-dev, libnewt-dev, libtextwrap-dev, libreadline-dev (>= 8.1.2-1.1), libdebian-installer4-dev | libdebian-installer-dev, libglib2.0-dev, libgtk2.0-dev <!pkg.cdebconf.nogtk>, libcairo2-dev <!pkg.cdebconf.nogtk>, libselinux1-dev [linux-any] | libselinux-dev [linux-any], dh-autoreconf, dh-exec
Package-List:
 cdebconf deb utils optional arch=any
 cdebconf-gtk deb admin optional arch=any profile=!pkg.cdebconf.nogtk
 cdebconf-gtk-udeb udeb debian-installer optional arch=any profile=!pkg.cdebconf.nogtk,!noudeb
 cdebconf-newt-udeb udeb debian-installer optional arch=any profile=!noudeb
 cdebconf-priority udeb debian-installer standard arch=all profile=!noudeb
 cdebconf-text-udeb udeb debian-installer optional arch=any profile=!noudeb
 cdebconf-udeb udeb debian-installer standard arch=any profile=!noudeb
 libdebconfclient0 deb libs optional arch=any
 libdebconfclient0-dev deb libdevel optional arch=any
 libdebconfclient0-udeb udeb debian-installer optional arch=any profile=!noudeb
Checksums-Sha1:
 6c7e77f8856b2a734273992b6aeb70558a62a2f7 285500 cdebconf_0.271ubuntu3.tar.xz
Checksums-Sha256:
 a4b242e7aef7923fd16d3aeb5a220ab6f4d27bc005b9d1e7d67449faaa68bcd1 285500 cdebconf_0.271ubuntu3.tar.xz
Files:
 823d1777a33187002652748bf50b4cc3 285500 cdebconf_0.271ubuntu3.tar.xz
Original-Maintainer: Debian Install System Team <debian-boot@lists.debian.org>

-----BEGIN PGP SIGNATURE-----

iQJOBAEBCgA4FiEErEg/aN5yj0PyIC/KVo0w8yGyEz0FAmYJENYaHHN0ZXZlLmxh
bmdhc2VrQHVidW50dS5jb20ACgkQVo0w8yGyEz2wrg/+L4NsIIxbuWjuJ+EvXyaL
g7nsXQboHpMtnsfPKwiTpz5llJuqBwMC/6fsroxCrPefVovy2bQBx3wodYFVwxko
Q/0TgoQYo6RkMxZREvevj53UNXc9UgUXmrxeKL57c2nAAVzKcfjN8BpgLYcH8Cu3
UOQ75AswcOn9TsXFZK6dDcrvxEJjeUNkjA/W8PF9/HYlGgJUl272zZXeJwAohFzZ
+Db4DOoU2uLRLvJ0akUJTl/EclRwTxusX1jCbCnDrS2VokUOIhSKE2/1FWYohUEi
2DcuLyAf9zdQPWH/CeHWxhbJvH8aoE/xSVSJkE2kqDZ2WKOaeEUP5P88eAawMIgM
Mxzhys/b1ZMuzrcSM26G9NDf/89ph6dPt0gpvp1zjuo7crQcSmLJY40tVVN9VT9o
fUWK1DfZuLrt4WBCROEu+Y6wOqYU2q+VidiHCVkwkfzOpW6cIoy6pwiqE2SQ+86Y
2qA095Qp8Gr9ZGC77RnycWJ+5Bp9Bcc7ESCC/j/o0YGIgjsSnxuuiU6B+ICngLdD
3YYFao1vY3GOfZ/ROsM1w19W+B1SDp515Agr5wwu4yW1AgzJ6mcG/OD56GToTkm0
pAl3v1HkMbkOq6HB1p0a/fWmIl1P6RwIE08En8ppoi76VHgwrVK3Tx3CrXuK4Kt5
TmIdgYmEEFD/HzrJ1mhwGNQ=
=m5E/
-----END PGP SIGNATURE-----
