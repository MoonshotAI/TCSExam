-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: libselinux
Binary: selinux-utils, libselinux1, libselinux1-dev, libselinux1-udeb, ruby-selinux, python3-selinux
Architecture: linux-any
Version: 3.5-2ubuntu2.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Laurent Bigonville <bigon@debian.org>, Russell Coker <russell@coker.com.au>
Homepage: https://selinuxproject.org
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/selinux-team/libselinux
Vcs-Git: https://salsa.debian.org/selinux-team/libselinux.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, pkg-config, python3-all
Build-Depends: debhelper-compat (= 13), dh-sequence-python3 <!nopython>, dh-sequence-ruby <!noruby>, file, libsepol-dev (>= 3.5), libpcre2-dev, libpython3-all-dev <!nopython>, pkg-config, python3-all-dev:any <!nopython>, python3-pip <!nopython>, python3-setuptools <!nopython>, swig <!nopython> <!noruby>
Package-List:
 libselinux1 deb libs optional arch=linux-any
 libselinux1-dev deb libdevel optional arch=linux-any
 libselinux1-udeb udeb debian-installer optional arch=linux-any profile=!noudeb
 python3-selinux deb python optional arch=linux-any profile=!nopython
 ruby-selinux deb ruby optional arch=linux-any profile=!noruby
 selinux-utils deb admin optional arch=linux-any
Checksums-Sha1:
 9f1ca79a767b2a69e63e01b82d13cff9bc712f4a 211453 libselinux_3.5.orig.tar.gz
 4129bdce451ef166f7e85321727d515b056d7d3c 981 libselinux_3.5.orig.tar.gz.asc
 50b814c6b5674f54e1e2716af7539c4c0c3b66b6 38112 libselinux_3.5-2ubuntu2.1.debian.tar.xz
Checksums-Sha256:
 9a3a3705ac13a2ccca2de6d652b6356fead10f36fb33115c185c5ccdf29eec19 211453 libselinux_3.5.orig.tar.gz
 fd37d441e0c08cabe9ac8f7815f52355bab2011549ec5792424fe18be9e1e015 981 libselinux_3.5.orig.tar.gz.asc
 13e47e0983f59235e34f5abe07a2a0d1af3dd2d255962c6a50fac4698c3fe891 38112 libselinux_3.5-2ubuntu2.1.debian.tar.xz
Files:
 8a52354fd7f8c85e9ed394e78f02201b 211453 libselinux_3.5.orig.tar.gz
 498b3b26ced1b9aab39cd74b812cff37 981 libselinux_3.5.orig.tar.gz.asc
 efc20a175dbc16cb5f5ea38b386a760b 38112 libselinux_3.5-2ubuntu2.1.debian.tar.xz
Original-Maintainer: Debian SELinux maintainers <selinux-devel@lists.alioth.debian.org>
Ruby-Versions: all

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEVovyKmYzfL/Jprm3LIPbyOm9DjcFAmb+Ie8ACgkQLIPbyOm9
DjfkdQ/+I9xZ1Ai5PKGy+XW50ohGsBrELb5yD1gxRJXEH3XgzB9WbiOeK03j7fYu
+N6X16Chn0fSJWWOPyAZmnvO8tcFI/I0dSm7TwNRGiG/m8MwP5XN2u9KHCsGy/ZT
8Kojp/x9q2ZxA+OvBOGtplXSzchEtjkTIMIUC3jZxTxfmuZPwxH3jctsmWZjjaf0
XxTnGttqiRstdZ5vSPAXSBoqxm/Urtneqw4IwXjBlMUZfm1vgglET3+fYhPG47lV
eYFQZX1egwCC5mH0qSXAvrna1GhSSmUYrcudDM2cbMHL1tjJfq4ZJsWABJo4Nk59
uqE+UyO+CifNJIcRJsYicb3zkFJLBqFcgLz7SPHP79VBRlVzJ180sgCq9Zf4XS0S
73O5tkpAqOLC+1iPAOWqjOdWq+Kiaip+3LUUbF9DnHDZXYw/oq2VQcOqkdg0f/2j
81LFuRHO/+EcTNeDqUJPVTD4zaZyMwuh+cjrHV1sXbyk/hONTorRSsMV4PZZjDJ5
pI85L8ojzUMyabZBhcfx2IJSAPvTn9d533Enb7hg2bKHXJjzLNuhnulhLicDWKpY
YE7Y3aHL2pqcjtxlrstlQxsxrinXHyeDUAB9w4JUukXRk6Tn/UaAJ0wysN+48Hht
JffmrVJtznoc0mc6aGVnxVLjuFFzLheZRNtBM3ZM/11ELQZq22c=
=4QbK
-----END PGP SIGNATURE-----
