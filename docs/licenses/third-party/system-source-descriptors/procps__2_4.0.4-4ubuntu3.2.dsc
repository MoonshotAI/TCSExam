-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: procps
Binary: procps, libproc2-0, libproc2-dev
Architecture: any
Version: 2:4.0.4-4ubuntu3.2
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Homepage: https://gitlab.com/procps-ng/procps
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/procps
Vcs-Git: https://salsa.debian.org/debian/procps.git
Testsuite: autopkgtest
Testsuite-Triggers: shunit2
Build-Depends: debhelper-compat (= 13), dh-exec (>= 0.3), libncurses-dev, dejagnu, libnuma-dev [amd64 i386 ia64 mips mipsel mips64 mips64el powerpc ppc64el], pkg-config, libsystemd-dev (>= 209) [linux-any]
Package-List:
 libproc2-0 deb libs optional arch=any
 libproc2-dev deb libdevel optional arch=any
 procps deb admin important arch=any
Checksums-Sha1:
 2b859acd7060e9898ac457dbd26dbebf563cc44b 1401540 procps_4.0.4.orig.tar.xz
 8cfb1ff6050ba2cd87f700a31bb3f93f9ebd4f96 38784 procps_4.0.4-4ubuntu3.2.debian.tar.xz
Checksums-Sha256:
 22870d6feb2478adb617ce4f09a787addaf2d260c5a8aa7b17d889a962c5e42e 1401540 procps_4.0.4.orig.tar.xz
 519e5cd39f4a8401dfd892134f3c5ccf5221f23fe32174393ce81cc45526f05e 38784 procps_4.0.4-4ubuntu3.2.debian.tar.xz
Files:
 2f747fc7df8ccf402d03e375c565cf96 1401540 procps_4.0.4.orig.tar.xz
 e82342021337e359addb9ed4971dcfa5 38784 procps_4.0.4-4ubuntu3.2.debian.tar.xz
Original-Maintainer: Craig Small <csmall@debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEpi0s+9ULm1vzYNVLFZ61xO/Id0wFAmb2d9oACgkQFZ61xO/I
d0xS4Q//Un5VSVJAYcjGhIg4D6oBawUdypBa7V7i/1WAdagGRZUeXkVQsmO2woSH
TXTLECYNNb323xa6ebbLG7BdK3elrji04jsxjXemou4zN+B4blVTZrLMZSuQf2Fc
B+0FLF6kpcoluNFE3T1+kUNZPyXgcbpaZVl76sZeO1oZQzD0OK8QoYm0i1EMOTPD
CjNHQZlEKQTiXJZiy6Bp0iE5Mx6BaZZdYxXc/ilOOi9WEuQdW/itTCyUPUMhIwHd
Z0rSVj9YecDk7of4nDPrpRWYcJQI3a8H6eqNiMSt64QkekPzryorNagt1+nXH2vR
BJpLRocwz0z9LHvLWlV1QyMhZF/4W8IgPZ68dF2GZlasza8nbs/UT5W1kEmKoIgo
nkyNKA4QIPhu9uN5Cn2zzisGlheN2ESACbYaLksKkf+tPtOlSHg5+STWYMlmZnoL
8WaW0/tA0esQM8lJiObuV0wTH4VKGZpsXzD9011PQAqI766yGlTcGCVFgJMWyiaO
K+xbIEMWkPZbpcqIonFeOLcaQVQ6CScWCLvE8BL2VfQZ56HQELu++fPq68mskbBs
v2cKtkkNs9Y3qgnNTvnjHmcP/ySLZbczKgGB8xW+rqkSzzwvpoMNAFIRnH78/THy
JCdnisXAUcojc6PuhcNBwqfJpeThsWWNwxU2xEI+K19CCcKyF10=
=QeHD
-----END PGP SIGNATURE-----
