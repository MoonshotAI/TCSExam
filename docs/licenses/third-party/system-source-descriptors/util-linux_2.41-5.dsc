-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: util-linux
Binary: util-linux, util-linux-locales, mount, bsdutils, bsdextrautils, fdisk, fdisk-udeb, libblkid1, libblkid1-udeb, libblkid-dev, libfdisk1, libfdisk1-udeb, libfdisk-dev, libmount1, libmount1-udeb, libmount-dev, libsmartcols1, libsmartcols1-udeb, libsmartcols-dev, libuuid1, uuid-runtime, libuuid1-udeb, uuid-dev, util-linux-udeb, rfkill, eject, eject-udeb, util-linux-extra, liblastlog2-2, liblastlog2-dev, libpam-lastlog2, lastlog2, login
Architecture: any all
Version: 2.41-5
Maintainer: Chris Hofstaedtler <zeha@debian.org>
Homepage: https://github.com/util-linux/util-linux
Standards-Version: 4.7.0
Vcs-Browser: https://salsa.debian.org/debian/util-linux
Vcs-Git: https://salsa.debian.org/debian/util-linux.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, expect, passwd, pkg-config
Build-Depends: debhelper-compat (= 13), dh-exec, dh-package-notes, dh-sequence-installsysusers, dh-sequence-zz-debputy-rrr (>= 0.1.23~), asciidoctor <!stage1 !nodoc>, bc <!stage1 !nocheck>, bison, flex, gettext, libaudit-dev [linux-any] <!stage1>, libcap-ng-dev [linux-any] <!stage1>, libcrypt-dev <!stage1>, libcryptsetup-dev [linux-any] <!pkg.util-linux.noverity>, libncurses-dev, libpam0g-dev <!stage1>, libreadline-dev, libselinux1-dev [linux-any], libsqlite3-dev, libsystemd-dev [linux-any] <!stage1>, libtool, libudev-dev [linux-any] <!stage1>, netbase <!stage1 !nocheck>, pkgconf, po-debconf, po4a, socat <!stage1 !nocheck>, systemd [linux-any] <!stage1>, systemd-dev [linux-any] <!stage1>, zlib1g-dev
Build-Conflicts: libedit-dev
Package-List:
 bsdextrautils deb utils optional arch=any profile=!stage1
 bsdutils deb utils required arch=any profile=!stage1 essential=yes
 eject deb utils optional arch=linux-any profile=!stage1
 eject-udeb udeb debian-installer optional arch=linux-any profile=!stage1,!noudeb
 fdisk deb utils important arch=any
 fdisk-udeb udeb debian-installer optional arch=hurd-any,linux-any profile=!stage1,!noudeb
 lastlog2 deb utils optional arch=any profile=!stage1
 libblkid-dev deb libdevel optional arch=any
 libblkid1 deb libs optional arch=any
 libblkid1-udeb udeb debian-installer optional arch=any profile=!noudeb
 libfdisk-dev deb libdevel optional arch=any
 libfdisk1 deb libs optional arch=any
 libfdisk1-udeb udeb debian-installer optional arch=any profile=!noudeb
 liblastlog2-2 deb libs optional arch=any
 liblastlog2-dev deb libdevel optional arch=any
 libmount-dev deb libdevel optional arch=linux-any
 libmount1 deb libs optional arch=any
 libmount1-udeb udeb debian-installer optional arch=linux-any profile=!noudeb
 libpam-lastlog2 deb admin optional arch=any profile=!stage1
 libsmartcols-dev deb libdevel optional arch=any
 libsmartcols1 deb libs optional arch=any
 libsmartcols1-udeb udeb debian-installer optional arch=any profile=!noudeb
 libuuid1 deb libs optional arch=any
 libuuid1-udeb udeb debian-installer optional arch=any profile=!noudeb
 login deb admin required arch=any profile=!stage1 protected=yes
 mount deb admin required arch=linux-any profile=!stage1
 rfkill deb utils optional arch=linux-any profile=!stage1
 util-linux deb utils required arch=any profile=!stage1 essential=yes
 util-linux-extra deb utils standard arch=any profile=!stage1
 util-linux-locales deb localization optional arch=all profile=!stage1
 util-linux-udeb udeb debian-installer optional arch=any profile=!stage1,!noudeb
 uuid-dev deb libdevel optional arch=any
 uuid-runtime deb utils optional arch=any profile=!stage1
Checksums-Sha1:
 1bf73b08c78569a52f9cd18f54b357e9135fa062 9535724 util-linux_2.41.orig.tar.xz
 512390fb0286cdcb4c34d9c5936d893649823f21 120144 util-linux_2.41-5.debian.tar.xz
Checksums-Sha256:
 81ee93b3cfdfeb7d7c4090cedeba1d7bbce9141fd0b501b686b3fe475ddca4c6 9535724 util-linux_2.41.orig.tar.xz
 20ad832160d5ed8de4759ce00652f620ce642ab583c3c1c431b68a15cdba1d07 120144 util-linux_2.41-5.debian.tar.xz
Files:
 e666a34b03554c18a1073347b16661ce 9535724 util-linux_2.41.orig.tar.xz
 181f86b5d10d8e2daf8ee6004564ac7c 120144 util-linux_2.41-5.debian.tar.xz

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEfRrP+tnggGycTNOSXBPW25MFLgMFAmgeiNwACgkQXBPW25MF
LgOAvw/+N1TivRjRP67v17gNXjqJn/uKubM2dsREBM48/TJ6nZwfeSHZURc9O1ex
n1QgdDHcXh7FwMXyfOY6WrvTN6ta08oROI/h5CYFcf0yS2LCdDkbePRjJBvWuWaj
SjCn83E8B3GQdGkl04FLDjTPtQccgGsF4dJRWAaxp7VUE4syd54Xvs5xYqvg3BKp
ml8lcpHfMt/koFYemhh20SJ55EBJmOmF2/6fvTaYk0xnP0IlJVmraf8/uXWewYDE
q6048rD5qYN3U9vmY1LrXlF1KyYC5EDJETPde/ISTPc1qm9ABdZDa+1r2MYSkqrj
Qq/fZf7UJ2179hSK0SlqN+oCGZlaU9ohXqj0fEEFv1aTJvLJUbulI/33RW9ZhzgD
zZjwnwk4AQoNOxnAMjlPfy/UQizb5AhGE8Doim+T9SNcBVfJ5RU9H1n9kyZ7vrQ/
ST/zp/wrp7EL5TDkeemtNHW5AhD75ZPLdAAtfJDIEfnecpVLWnInkpdIsMFtPl+Q
UeMrbfvqTrSoXFLJSjp7t1+cvto6TfpqWlIWWLE5MxzvYYp+enSXbm6GQSSljvEg
BWfQwqFAxU1JpYrqoXFY0DLYQe+z5pGYMHm9QY/QEUhh/9hygiOz3sahM7Zk490m
b5+4vz75tr9Vgx41EQ8YLVLhY2lVHmueZqKl4Ut6K1HOrCap00Y=
=If1P
-----END PGP SIGNATURE-----
