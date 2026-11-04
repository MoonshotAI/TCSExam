-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: curl
Binary: curl, libcurl4t64, libcurl3t64-gnutls, libcurl4-openssl-dev, libcurl4-gnutls-dev, libcurl4-doc
Architecture: any all
Version: 8.5.0-2ubuntu10.11
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Carlos Henrique Lima Melara <charlesmelara@riseup.net>, Samuel Henrique <samueloph@debian.org>, Sergio Durigan Junior <sergiodj@debian.org>
Homepage: https://curl.se/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/curl
Vcs-Git: https://salsa.debian.org/debian/curl.git
Testsuite: autopkgtest
Testsuite-Triggers: @builddeps@, gcc, libc-dev, libcurl-dev, libldap-dev, pkgconf, slapd
Build-Depends: dpkg-dev (>= 1.22.5), debhelper-compat (= 13), autoconf, automake, ca-certificates, dh-exec, groff-base, libbrotli-dev, libgnutls28-dev, libidn2-dev, libkrb5-dev, libldap2-dev, libnghttp2-dev, libpsl-dev, librtmp-dev, libssh-dev, libssh2-1-dev, libssl-dev, libtool, libzstd-dev, locales-all <!nocheck>, openssh-server <!nocheck>, python3:native <!nocheck>, python3-impacket [!i386] <!nocheck>, gnutls-bin [amd64 arm64 armel armhf i386 mips64el mipsel s390x powerpc ppc64 riscv64] <!nocheck>, quilt, stunnel4 [!i386] <!nocheck>, zlib1g-dev
Build-Conflicts: autoconf2.13, automake1.4
Package-List:
 curl deb web optional arch=any
 libcurl3t64-gnutls deb libs optional arch=any
 libcurl4-doc deb doc optional arch=all
 libcurl4-gnutls-dev deb libdevel optional arch=any
 libcurl4-openssl-dev deb libdevel optional arch=any
 libcurl4t64 deb libs optional arch=any
Checksums-Sha1:
 d7877b39b6efda66e9ac5f9c28b8b28d8c0b7b7e 4372979 curl_8.5.0.orig.tar.gz
 2bad3ec8c431fb952497e58eca0cf2ba73fdecb0 82508 curl_8.5.0-2ubuntu10.11.debian.tar.xz
Checksums-Sha256:
 05fc17ff25b793a437a0906e0484b82172a9f4de02be5ed447e0cab8c3475add 4372979 curl_8.5.0.orig.tar.gz
 8f75497af2a5367b50d4a69276dab864388823c8a45c1e5d73c1c430fa5138a2 82508 curl_8.5.0-2ubuntu10.11.debian.tar.xz
Files:
 0bc69288b20ae165ff4b7d6d7bbe70d2 4372979 curl_8.5.0.orig.tar.gz
 e716efbe52c159a1bf99417812f0a218 82508 curl_8.5.0-2ubuntu10.11.debian.tar.xz
Original-Maintainer: Debian Curl Maintainers <team+curl@tracker.debian.org>

-----BEGIN PGP SIGNATURE-----

iQJPBAEBCgA5FiEEuEg4xBTSeUWY0Nx77tH0LvjAvecFAmpNHsAbHGt5bGUua2Vy
bmlja0BjYW5vbmljYWwuY29tAAoJEO7R9C74wL3nQz4QAI39SWaERKKpRgUb3VMR
fjgli4+uqzp2Q00eAPL7blS5HVscypfoqxdBIOtHjt0unP1hJ5v6Zj5wfe7GmWPl
5hOwdbyDuCppZLH1hrxIk/jjfwpELtzDvdHK2EeEwwSwA90dPHmlgTbKCJuyHEZe
fhK7ReSDYZUuphpelRlSlcv6STZCJs8AFoKDxK9EoEgtZ0eN2Ap3hqzL0Blm9IWQ
qwvrmqh6jmp9UMlw8tZTW1ZunOQSiq2m+seBB8ab7yvoMD2CYLmDAzR/NchzCcid
XTjSbzIsyiSm3Eq2gSvaGafvSLZP1iVKUd/I6pqLt55Xxz+y04THsKwkTyyVm5Di
fhD8+FLain/nqtwy5d1Qx4r1NGeOnINq5/qaRSJp8jEjl2A1on2EHj+hScPddPoE
2EMR0pshwCwPcq29YJ1OhTn9NIvChoL4cZgncExVroZiDyE6m2i2JJ0OpwzeFif6
nFKY7qZEx0qn6HJq6Bnn0lBFO97wG9nNPFYro3YjAyZ8JLaPgliGQi57g3nixMOZ
tAhC5//xZ3p2Czp0OvHK85V7YkIcVTEEWRTbTTlWIvnjc74tPwr/dczzOmC0syKA
yrGYVn4fw4akoN7CrfKgo6f87Fu4aKSM0S9FclzMzYX9swZsBGMuyrta6AbUG5gu
mKgeBzsr6W0LbIawoavoe6Gm
=SeRl
-----END PGP SIGNATURE-----
