-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: util-linux
Binary: util-linux, util-linux-locales, mount, bsdutils, bsdextrautils, fdisk, fdisk-udeb, libblkid1, libblkid1-udeb, libblkid-dev, libfdisk1, libfdisk1-udeb, libfdisk-dev, libmount1, libmount1-udeb, libmount-dev, libsmartcols1, libsmartcols1-udeb, libsmartcols-dev, libuuid1, uuid-runtime, libuuid1-udeb, uuid-dev, util-linux-udeb, rfkill, eject, eject-udeb, util-linux-extra
Architecture: any all
Version: 2.39.3-9ubuntu6.5
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders:  Chris Hofstaedtler <zeha@debian.org>
Homepage: https://www.kernel.org/pub/linux/utils/util-linux/
Standards-Version: 4.6.0
Vcs-Browser: https://salsa.debian.org/debian/util-linux
Vcs-Git: https://salsa.debian.org/debian/util-linux.git
Testsuite: autopkgtest
Testsuite-Triggers: bash, bc, build-essential, dpkg, grep, pkg-config
Build-Depends: asciidoctor <!stage1 !nodoc>, bc <!stage1 !nocheck>, bison, debhelper-compat (= 13), dh-exec, gettext, libaudit-dev [linux-any] <!stage1>, libcap-ng-dev [linux-any] <!stage1>, libcrypt-dev <!stage1>, libcryptsetup-dev [linux-any] <!pkg.util-linux.noverity>, libncurses-dev, libpam0g-dev <!stage1>, libreadline-dev, libselinux1-dev [linux-any], libsystemd-dev [linux-any] <!stage1>, libtool, libudev-dev [linux-any] <!stage1>, netbase <!stage1 !nocheck>, pkg-config, po-debconf, po4a, socat <!stage1 !nocheck>, systemd [linux-any] <!stage1>, systemd-dev [linux-any] <!stage1>, zlib1g-dev
Build-Conflicts: libedit-dev
Package-List:
 bsdextrautils deb utils optional arch=any profile=!stage1
 bsdutils deb utils required arch=any profile=!stage1 essential=yes
 eject deb utils optional arch=linux-any profile=!stage1
 eject-udeb udeb debian-installer optional arch=linux-any profile=!stage1,!noudeb
 fdisk deb utils important arch=any profile=!stage1
 fdisk-udeb udeb debian-installer optional arch=hurd-any,linux-any profile=!stage1,!noudeb
 libblkid-dev deb libdevel optional arch=any
 libblkid1 deb libs optional arch=any
 libblkid1-udeb udeb debian-installer optional arch=any profile=!noudeb
 libfdisk-dev deb libdevel optional arch=any
 libfdisk1 deb libs optional arch=any
 libfdisk1-udeb udeb debian-installer optional arch=any profile=!noudeb
 libmount-dev deb libdevel optional arch=linux-any
 libmount1 deb libs optional arch=any
 libmount1-udeb udeb debian-installer optional arch=linux-any profile=!noudeb
 libsmartcols-dev deb libdevel optional arch=any
 libsmartcols1 deb libs optional arch=any
 libsmartcols1-udeb udeb debian-installer optional arch=any profile=!noudeb
 libuuid1 deb libs optional arch=any
 libuuid1-udeb udeb debian-installer optional arch=any profile=!noudeb
 mount deb admin required arch=linux-any profile=!stage1
 rfkill deb utils optional arch=linux-any profile=!stage1
 util-linux deb utils required arch=any profile=!stage1 essential=yes
 util-linux-extra deb utils standard arch=any profile=!stage1
 util-linux-locales deb localization optional arch=all profile=!stage1
 util-linux-udeb udeb debian-installer optional arch=any profile=!stage1,!noudeb
 uuid-dev deb libdevel optional arch=any
 uuid-runtime deb utils optional arch=any profile=!stage1
Checksums-Sha1:
 9704d9927be7888b97a09735a1b5915a390d43c3 8526168 util-linux_2.39.3.orig.tar.xz
 25501d9e4d85dfe2747c2af218380f77504c82b6 148016 util-linux_2.39.3-9ubuntu6.5.debian.tar.xz
Checksums-Sha256:
 7b6605e48d1a49f43cc4b4cfc59f313d0dd5402fa40b96810bd572e167dfed0f 8526168 util-linux_2.39.3.orig.tar.xz
 e0130fe89b648a42710af003c965f9622707c69045aab442d17e028e232f105c 148016 util-linux_2.39.3-9ubuntu6.5.debian.tar.xz
Files:
 f3591e6970c017bb4bcd24ae762a98f5 8526168 util-linux_2.39.3.orig.tar.xz
 10f3ce1cd956f70cb9f3c7c988431942 148016 util-linux_2.39.3-9ubuntu6.5.debian.tar.xz
Original-Maintainer: util-linux packagers <util-linux@packages.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmmrLbwACgkQZWnYVadE
vpPMEw//Yrpyeobc+UemjImwdaAjYbgl3X/M5Mmnlmo6xnw+UBX3PsYRRBnWdfF2
4mLcRlLaXRy7Y3qiy4LbBmFCON80oMpWBka81Fc1tHnq8TfxwUiboyWwwMiN4mRd
7eY1e34qo8ySfL8QdjyxemwBJt7KxXjYYnL9PM2F73yi7WKOCsEDbu8CzwNvaxOo
cbUuDxXlbe8vYKM7OdnT7Herf+IGJ4PEIlFwlJkpUdtTdFnThG0O/icQwapXkghK
As8uX1Dh3uDKBKHpILxfXXtnXwudUOx8k5fK9wBD0KC4mKoiR7mW1CETPOqlahol
0tV3pCgqAEB1FmT0sLhDME6zeFiH71LI/IP8XA6ixDTFbJfOVo+u7mXoMt3GKhCK
a4MQ3CZyvvxtmDe3uLTRhQIg2kOYo/2vjwhDS4ZlFhIG57U82oNrhqPHIe2T9E5L
U/HTnbgINmyA6nSucDMPHApVAxwE8T6y1hcWFO0YyUrinnN9bM8wLS5/2RIaa7IU
+8bBbtSkPlk4qPUy1kWRMCPCPewVLzdkDZ4kqKP5wGnr2GZqlFSA4+BSCPUbLwyk
d5M9vUbhafU1atcfhBuctaprOZpby3/NgFKRW8rQvMNT7uZnsoreKwZIz6UE7o9I
S8sWqEXS+gSYRUDD41XMRJ9qGcG1djOI6N0ybgElwmXMfr/S2eo=
=twxD
-----END PGP SIGNATURE-----
