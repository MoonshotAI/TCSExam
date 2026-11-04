-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: tzdata
Binary: tzdata, tzdata-icu, tzdata-legacy
Architecture: all
Version: 2026e-0ubuntu0.24.04.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Clint Adams <clint@debian.org>, Aurelien Jarno <aurel32@debian.org>, Benjamin Drung <bdrung@debian.org>
Homepage: https://www.iana.org/time-zones
Standards-Version: 4.6.2
Vcs-Browser: https://code.launchpad.net/~ubuntu-core-dev/ubuntu/+source/tzdata/+git/tzdata
Vcs-Git: https://git.launchpad.net/~ubuntu-core-dev/ubuntu/+source/tzdata -b ubuntu/noble
Testsuite: autopkgtest
Testsuite-Triggers: g++, python3, python3-debian, python3-icu
Build-Depends: debhelper-compat (= 13)
Build-Depends-Indep: gawk, icu-devtools, po-debconf, python3 (>= 3.9), python3-debian, python3-natsort, python3-polib
Package-List:
 tzdata deb localization required arch=all
 tzdata-icu deb localization optional arch=all
 tzdata-legacy deb localization optional arch=all
Checksums-Sha1:
 119a62cdde6126115c42c733be1db12d0ee8d11e 481989 tzdata_2026e.orig.tar.gz
 77d5204f862de12e83acf3a891274f8ebfa185cf 833 tzdata_2026e.orig.tar.gz.asc
 88be5c9cfac2f14feaf96cc5bb162501505ea824 189608 tzdata_2026e-0ubuntu0.24.04.1.debian.tar.xz
Checksums-Sha256:
 b26882805f26aac59d5b222978e6580484b834ccdc98be89df2f05a6dc53a652 481989 tzdata_2026e.orig.tar.gz
 91b37052145786c4a238115bc69f5edb947d9cdd19164910c40c249be27a7eda 833 tzdata_2026e.orig.tar.gz.asc
 3a4832de76177e0f77785b9a538a335ef8638c29f6986b844443dc3fe6dc6cb6 189608 tzdata_2026e-0ubuntu0.24.04.1.debian.tar.xz
Files:
 e1bb044ee184daee12f3e83ca16def7f 481989 tzdata_2026e.orig.tar.gz
 2b2d7c65fa18bff735fd682d0d87146d 833 tzdata_2026e.orig.tar.gz.asc
 bdbaf0ca5fc1b51e5912c2872673c92f 189608 tzdata_2026e-0ubuntu0.24.04.1.debian.tar.xz
Original-Maintainer: GNU Libc Maintainers <debian-glibc@lists.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEpi0s+9ULm1vzYNVLFZ61xO/Id0wFAmrDa+YACgkQFZ61xO/I
d0wevxAAi8o+qoZv8wFtOLFuMiLzpEq1md6IluwAuoBGrbd9H2tUQTtfGmf0xEY4
hMHAJbJkEjSRrLDT6a3SufFcFd14Lv6s5gRYY05bR3x4u94ix7Ookw5gkvnsUY3E
0VF3KdWseNwuiEDrjzjEVgKgI0ZsNlP5K1ysvakaq+ieT6jsb3cuS+lf8TuMujf2
+tEBZe3/TAEHfs+uWalRas0MOROx4BU6jNe8L6xGgbvXa7bnXCZyZ3uQWid1Xi0l
/NxswRHkw2uCF/tNh+xAiNWGj0rG7ZJYlsFcdFPzvnmW+giss8XIL48czNfdWFqp
e95o01EneH2PCb5vWUBDTtTyy4LikuRqVkjsO1oGfEAnKs9hP7YhNIX+sHYm60if
GNq8s6QZhPLPcj9DjPFtPArAefRrBCKUDJpQlhQtI7V5Au3r6R16HLJI9vNRPxrO
a3yGtn9U9gABQ/oBVydOU5mu7GZBi9H8gnhEN4pdttr4FvC3TQLIeIAi3zN9vye/
HnjHH/jiVhfOBQtteMpVmQnxZnprXpXpf5aL36ZsQkE103a7SouQ0QUMpu71RxJl
5hliy6Nws/fISUvPmz7yH+OFSfTezY3cPIBJgA2syLb5T4Vq7qqdfoMiR1BZKq39
rKqil+SKCMY8CLuOxiZUGA4qbLAzdT7lzYXrLNOkZCtC8NK8zlg=
=du11
-----END PGP SIGNATURE-----
