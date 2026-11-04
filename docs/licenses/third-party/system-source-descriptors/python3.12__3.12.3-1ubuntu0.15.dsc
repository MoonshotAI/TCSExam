-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: python3.12
Binary: python3.12, python3.12-venv, libpython3.12-stdlib, python3.12-minimal, python3.12-nopie, libpython3.12-minimal, libpython3.12t64, python3.12-examples, python3.12-dev, libpython3.12-dev, libpython3.12-testsuite, idle-python3.12, python3.12-doc, python3.12-dbg, libpython3.12t64-dbg, python3.12-full
Architecture: any all
Version: 3.12.3-1ubuntu0.15
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
 7de340d39664ac533b43ef92b1d1477d1600d838 299248 python3.12_3.12.3-1ubuntu0.15.debian.tar.xz
Checksums-Sha256:
 56bfef1fdfc1221ce6720e43a661e3eb41785dd914ce99698d8c7896af4bdaa1 20625068 python3.12_3.12.3.orig.tar.xz
 93ebdbc4df76a3438984e9da8670decd5bc35ea7e340787c69da61818d32b5a7 299248 python3.12_3.12.3-1ubuntu0.15.debian.tar.xz
Files:
 8defb33f0c37aa4bdd3a38ba52abde4e 20625068 python3.12_3.12.3.orig.tar.xz
 c65bf4dd197e0f775878030b3a19a7aa 299248 python3.12_3.12.3-1ubuntu0.15.debian.tar.xz
Original-Maintainer: Matthias Klose <doko@debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmo6gKEACgkQZWnYVadE
vpOVsRAAs9GwLgtC4rqDa/ziHHbEbWMcXCD9qZ4KAOpSDxtLZoR0/Ux8ne/g+jvb
HmlAJKUQy+hRmRrsl5JvhZ5i/45KXdZZy1zBCj4rZCeDlxofKw516K7PqCASc7Lp
5Lp7/nCbLwhmzIHwn16GUS9Yn7iW9w95JRqHv6Q/9HYgvNibjhH4YphGGnSoiNh3
OXiIrlGTz4i7i55VQX9LeswiVP5foM1MVBPmqZpFPPztgfLRDZOr5AeOzTNUjYr1
5c8DTlbsniQTbKSiHUDtQi6suZ5tq5vznoXGsInJyrAKDuKnrPanP/katr189+jD
/Bs4tW/qvndT6IRfTtwna0pC42IYRD358hQ6WP4vMSsJTNHJs6wya+tuIY9RP0wk
wstVXBCiS+HN+FyJ232HG7Vfqp1Q70dum67/He5Zxz5EC+hDXZ8fYrXcMzCgfEWI
P/x1QEDsvq6w8W4OFYmx3eqEh3463jWf6TnR7SR+Q619O54nfIjUhoWrNXllmeqc
SeFoGnUgSjZYh9aySgEUAiS+RpWek/3escamNsWGOmykhbSL2eRTsQnYJZYp09QW
o1XfL8PesG1N7jwm+zbXj8NkCAb5v9FJNhirv9pglNhdekStMdIsaXue3Rpv4lBd
+TK36F7/OncSNnunf7LOsOb6ZHXcis0zXj2LATe8LUZvsSVVKyk=
=THfB
-----END PGP SIGNATURE-----
