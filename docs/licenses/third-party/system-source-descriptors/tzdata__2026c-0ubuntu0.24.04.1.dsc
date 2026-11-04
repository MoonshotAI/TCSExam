-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: tzdata
Binary: tzdata, tzdata-icu, tzdata-legacy
Architecture: all
Version: 2026c-0ubuntu0.24.04.1
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
 25e5390e8b06c4dd9a7dea4d4a079631c1dd312e 475694 tzdata_2026c.orig.tar.gz
 ff388761981f8a9754f06876c3ba96b560149882 833 tzdata_2026c.orig.tar.gz.asc
 d0370eee27acd6f70b2911ee5f521c9512068e75 188348 tzdata_2026c-0ubuntu0.24.04.1.debian.tar.xz
Checksums-Sha256:
 e4a178a4477f3d0ea77cc31828ff72aa38feff8d61aa13e7e99e142e9d902be4 475694 tzdata_2026c.orig.tar.gz
 26cd02e034eed682aa911d224bca3247ff15914df317e3bb0b1a01dc557b46fe 833 tzdata_2026c.orig.tar.gz.asc
 a684e31c7c6e747a9aed337006ac53845c545f6e9129e73062d7c43774a36f63 188348 tzdata_2026c-0ubuntu0.24.04.1.debian.tar.xz
Files:
 bff7174205cefab793e3b24271ef2f45 475694 tzdata_2026c.orig.tar.gz
 f3ad86f24f90d2b0dfc6fdc9b5424f3f 833 tzdata_2026c.orig.tar.gz.asc
 9af0d7a1472836bb9c612479c8aac1ae 188348 tzdata_2026c-0ubuntu0.24.04.1.debian.tar.xz
Original-Maintainer: GNU Libc Maintainers <debian-glibc@lists.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEpi0s+9ULm1vzYNVLFZ61xO/Id0wFAmpaJSEACgkQFZ61xO/I
d0zvdg/+LQtWtzDRvg3Suto9SntLG5tqMjJpTMWW1CHhbER/IwacDncyi4ffbD+P
OKRFSSnM8wAxwgwHMdR9tBMX22NelWmEPKP3Ug/HqfcbGbzVsPnkFh4YEbvFADiJ
FsyDePo0IiOXzjKjMaiAtdIoUzS2h1q6pYeR6MMaHrxx+0ngdet6GWYeR3BKw3Td
6uGS4gVIyMpLtnt6xqHcGmrcIaHKgx2WiX7MwZRLMt2XjdgNHFI48voYzFQUJTtd
WwHqA0SAQA3bZUdVrKx34AmdtOQaU9GL37EmrMiPp5Zm7zLBbD1DYL7NZvcp43SE
tKOuYi/btv1b4uvDQyH4JfnoEcLkvDKEYmdIYkGV7zbMxCZETBMoeruQpyjo3sVK
4l4bg2r6hjYBbNZMOpkwbet7GtjxWdAUmKsSerbvsy2hH6HryGgoAB5g2piZ8yu9
s7aKXdz+MWMbEtHX4zAdkg4O3tfDq6oMMWcNAOVJLirIFiyI7PqK/K4jHAEMaTUy
OwjtvWJiUPIprUg8v4Y6QQ8f8OHtMKuDmZLJXbHR/DByFq7U0C2qTdyvCGUdo54s
++722ygWdYXpZWdfcEducpr48SaG/iNpVkJF70LH8xDE9TNFa45BUJ/KxoXsrLPQ
XRpMbLjU7KmBebXHa4mhlmsjBU3vIxg2GhFU898+9foyAg5K6NM=
=r4xi
-----END PGP SIGNATURE-----
