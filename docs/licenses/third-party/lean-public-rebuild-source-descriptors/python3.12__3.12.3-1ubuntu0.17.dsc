-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: python3.12
Binary: python3.12, python3.12-venv, libpython3.12-stdlib, python3.12-minimal, python3.12-nopie, libpython3.12-minimal, libpython3.12t64, python3.12-examples, python3.12-dev, libpython3.12-dev, libpython3.12-testsuite, idle-python3.12, python3.12-doc, python3.12-dbg, libpython3.12t64-dbg, python3.12-full
Architecture: any all
Version: 3.12.3-1ubuntu0.17
Maintainer: Ubuntu Core Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Stefano Rivera <stefanor@debian.org>
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/cpython-team/python3
Vcs-Git: https://salsa.debian.org/cpython-team/python3.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, ca-certificates, gdb, locales-all, python3-distutils, python3-gdbm, python3-gdbm-dbg, python3-pip, python3-setuptools, python3-setuptools-whl, python3-tk, python3-tk-dbg, python3-wheel-whl, shunit2, systemtap-sdt-dev, virtualenv
Build-Depends: debhelper (>= 11), dpkg-dev (>= 1.17.11), quilt, autoconf, lsb-release, sharutils, libreadline-dev | libeditreadline-dev, libncurses-dev, zlib1g-dev, libbz2-dev, liblzma-dev, libgdbm-dev, libdb-dev, libssl-dev, libexpat1-dev, libbluetooth-dev [linux-any] <!pkg.python3.12.nobluetooth>, locales-all, libnsl-dev, libsqlite3-dev, libffi-dev (>= 3.0.5) [!or1k], libgpm2 [linux-any], media-types | mime-support, netbase, bzip2, time, python3:any, python3.12:any <cross>, net-tools, systemtap-sdt-dev [!hurd-amd64 !hurd-i386], valgrind-if-available
Build-Depends-Indep: python3-sphinx, python3-docs-theme, texinfo
Package-List:
 idle-python3.12 deb python optional arch=all
 libpython3.12-dev deb libdevel optional arch=any
 libpython3.12-minimal deb python optional arch=any
 libpython3.12-stdlib deb python optional arch=any
 libpython3.12-testsuite deb libdevel optional arch=all
 libpython3.12t64 deb libs optional arch=any
 libpython3.12t64-dbg deb debug optional arch=any
 python3.12 deb python optional arch=any
 python3.12-dbg deb debug optional arch=any
 python3.12-dev deb python optional arch=any
 python3.12-doc deb doc optional arch=all
 python3.12-examples deb python optional arch=all
 python3.12-full deb python optional arch=any
 python3.12-minimal deb python optional arch=any
 python3.12-nopie deb python optional arch=any
 python3.12-venv deb python optional arch=any
Checksums-Sha1:
 3df73004a9b224d021fd397724e8bd4f9b6cc824 20625068 python3.12_3.12.3.orig.tar.xz
 13edb00b66d1217711ab02bb2a8043e125275736 302472 python3.12_3.12.3-1ubuntu0.17.debian.tar.xz
Checksums-Sha256:
 56bfef1fdfc1221ce6720e43a661e3eb41785dd914ce99698d8c7896af4bdaa1 20625068 python3.12_3.12.3.orig.tar.xz
 17b15629cb10825924cf7b85055255080ec773133ae0f8b8ce5ea2eec90dd200 302472 python3.12_3.12.3-1ubuntu0.17.debian.tar.xz
Files:
 8defb33f0c37aa4bdd3a38ba52abde4e 20625068 python3.12_3.12.3.orig.tar.xz
 0c581b10ce6695007736f0c27eb98732 302472 python3.12_3.12.3-1ubuntu0.17.debian.tar.xz
Original-Maintainer: Matthias Klose <doko@debian.org>

-----BEGIN PGP SIGNATURE-----

iQJOBAEBCgA4FiEEhC9y9XdAFQPCvYXchGmXSGiknnUFAmqWryQaHGFsbGVuLmh1
YW5nQGNhbm9uaWNhbC5jb20ACgkQhGmXSGiknnWGaRAAvIsdg1C42dMV3LSADQ8A
hPAXxflny8XgD6Raw1YxVgE7LWkDjgxmFYOPJ1pykh8J0n+ZuMQdeSXOh4XFM642
I6DY7vnBDafW5QxzZS4eDz0sbzk+KF3PdchzTIe6kW16bpI0lT+36Ds5uYuG38Vu
g7sJ8q8dhqFcACoZSWSGO8Z4QN3PqRgB9XR7oflut+SK4K9SM+aa91Js+GYTlkln
vRMldfyaUZ5thQASIGFnXCtjPg9dJKjEB2qol4MVdi1D3K4e7zXlGBM7fE6Gh3qU
AIjyqtkOSfVuxjoX0jgVgVKRYwa30SRYc03joyALqlwLcLiJTR3bVQfXgDRbIVBQ
2ml3+vN6HSadgOrXH1XQJtE6SDWLXbUQ6F8MKgqGVvFxvmMfzCQDM0wvL7W+KSGL
aj6t8QSUgESptkNFNkrLj2IqAq3L/bqCUhdE8M17MdJkIGvYz03DddspN/AH70KB
KgyoNk0GPNzZJdfBvzuXt8kpByKKmjzpxY+fUVwUSOvnn7NMLzF2yQecL5C50DGm
OpUEQbH/kTBMAjmaadyMjR2Keog94Jvq9LbTWl+izeEDDXlei+wbDGsPrtRqxhP5
VM2C6yhZ0rwgoKy+ziyRhu0pkl1uTmwDXNNdWzZLERUeLu97y2Km0cclic92ISZJ
/ZB49BhuxoRZD75JEhuLvmU=
=9fe1
-----END PGP SIGNATURE-----
