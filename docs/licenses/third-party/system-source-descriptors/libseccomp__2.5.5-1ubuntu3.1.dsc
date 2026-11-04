-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: libseccomp
Binary: libseccomp-dev, libseccomp2, seccomp, python3-seccomp
Architecture: linux-any
Version: 2.5.5-1ubuntu3.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Luca Bruno <lucab@debian.org>, Felix Geyer <fgeyer@debian.org>
Homepage: https://github.com/seccomp/libseccomp
Standards-Version: 3.9.7
Vcs-Browser: https://salsa.debian.org/debian/libseccomp
Vcs-Git: https://salsa.debian.org/debian/libseccomp.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, linux-libc-dev
Build-Depends: debhelper-compat (= 12), linux-libc-dev, dh-python <!nopython>, python3-all-dev:any <!nopython>, libpython3-all-dev <!nopython>, cython3:native <!nopython>, python3-setuptools <!nopython>, valgrind [amd64 arm64 armhf i386 mips mips64 powerpc ppc64 ppc64el s390x] <!nocheck>, gperf
Package-List:
 libseccomp-dev deb libdevel optional arch=linux-any
 libseccomp2 deb libs optional arch=linux-any
 python3-seccomp deb python optional arch=linux-any profile=!nopython
 seccomp deb utils optional arch=linux-any
Checksums-Sha1:
 c0349aca443ec0807528d088a3f2e2e0d5d1b17b 642445 libseccomp_2.5.5.orig.tar.gz
 9a734ef6a09c03a43d9b90ae631be5e60fb00e28 833 libseccomp_2.5.5.orig.tar.gz.asc
 87f83b14464dffe6029b873b24a9483d3d566d7f 24484 libseccomp_2.5.5-1ubuntu3.1.debian.tar.xz
Checksums-Sha256:
 248a2c8a4d9b9858aa6baf52712c34afefcf9c9e94b76dce02c1c9aa25fb3375 642445 libseccomp_2.5.5.orig.tar.gz
 f3bf8a946020d3047581f11fe6ac71971a842115ddb362562b193861ef57d97b 833 libseccomp_2.5.5.orig.tar.gz.asc
 ee1e79bc46f18a992ac80f349fdd5cfa0b5f2f6b298473b587c7cf5af89a8df6 24484 libseccomp_2.5.5-1ubuntu3.1.debian.tar.xz
Files:
 c27a5e43cae1e89e6ebfedeea734c9b4 642445 libseccomp_2.5.5.orig.tar.gz
 c098d8cb3827dcdd038a5ffeab897311 833 libseccomp_2.5.5.orig.tar.gz.asc
 85b1fff51282cc5384e900d6cf5d09e9 24484 libseccomp_2.5.5-1ubuntu3.1.debian.tar.xz
Original-Maintainer: Kees Cook <kees@debian.org>
-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEVovyKmYzfL/Jprm3LIPbyOm9DjcFAma1glwACgkQLIPbyOm9
DjfXcQ/+P+KH8TjYRUwJmxHFebnAC4LUUiF1wdH/ovFjIbtBW/UjOj4y2CZcCW8x
5kTN8TRN2fwzaGSYV9oxdXi+ir9YswG1z9etatiibhJeFoZicyYrAzaqDBAkuPLc
5nWMPOXnrLfVhnhryLnf+fDHejJt0Ai2PrH6NSQIQtAEam82hQ/P487VnNHxvdyH
CL6FB0dcbCenxD6H1djO8JYMiWwM7C7AndfRpisZsfywr+op+zbkKXB4ccOqc17r
ePD+Ntvl5L1JBzTlD8hOv4EW126PDUnsL7Tq4kYtmrLFF8SnOA1UNO6fvEia6Lzk
S1cJqpMOGP9CEyo/Ov2mc568YXaW/Rjp7H0swgavlASULLMYD2VI+32TUmJu0Aa9
70FS6h2iAyTdXC0+dHuWrWMDGG0HyLMyPNKnweSoXcDwO/N7wDcwzjgaoXVbZiZh
VR1ezSAYwmCcxuiz8CO8zvDV50zBvlkmH1OqdDsLwPOsn6sgAOeQsg1RCZVJI9SA
cA6KPWcaRu/xOwYTAfljuOjYit2NQUiMAwKX/BTAtLYZD2MEZ28z3p48BJWH1Vbm
a/R6Q0TUWYHt7saAsML7DmDYEzRyBzNAUFkKSQx5DfUAt1KuRL22N7E+uJgjiaVG
sc+WZkGymZS9rpcGVPqCLpwt8gIeYPTXrpOkr67/Uy+NZZKWDzM=
=itS5
-----END PGP SIGNATURE-----
