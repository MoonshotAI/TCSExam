-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: libgpg-error
Binary: libgpg-error-dev, libgpg-error0, gpgrt-tools, libgpg-error0-udeb, libgpg-error-mingw-w64-dev, libgpg-error-l10n
Architecture: any all
Version: 1.47-3build2.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders:  Daniel Kahn Gillmor <dkg@fifthhorseman.net>, Christoph Biedl <debian.axhn@manchmal.in-ulm.de>,
Homepage: https://www.gnupg.org/related_software/libgpg-error/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/libgpg-error
Vcs-Git: https://salsa.debian.org/debian/libgpg-error.git -b debian/unstable
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, gcc-mingw-w64-i686, gcc-mingw-w64-x86-64, pkg-config, wine32, wine64
Build-Depends: automake (>= 1.14), debhelper-compat (= 13), gettext (>= 0.19.3), texinfo
Build-Depends-Indep: mingw-w64
Package-List:
 gpgrt-tools deb devel optional arch=any
 libgpg-error-dev deb libdevel optional arch=any
 libgpg-error-l10n deb localization optional arch=all
 libgpg-error-mingw-w64-dev deb libdevel optional arch=all
 libgpg-error0 deb libs optional arch=any
 libgpg-error0-udeb udeb debian-installer optional arch=any profile=!noudeb
Checksums-Sha1:
 94668233fd7bd8e7c0ec5e363134cd53c575da60 1020862 libgpg-error_1.47.orig.tar.bz2
 8d7a5385afb1d1c64c99fc566d01009f97c16595 228 libgpg-error_1.47.orig.tar.bz2.asc
 f7b811d0d4ccdd3104af3c03b5987b652a7910c3 18776 libgpg-error_1.47-3build2.1.debian.tar.xz
Checksums-Sha256:
 9e3c670966b96ecc746c28c2c419541e3bcb787d1a73930f5e5f5e1bcbbb9bdb 1020862 libgpg-error_1.47.orig.tar.bz2
 6ab547bf020761e1df80b08335773a91c345ff2c1344f15b1f7d195293ab21a5 228 libgpg-error_1.47.orig.tar.bz2.asc
 f02a079a6ddf9930659c3402820b6bd190687e8f1c223f340c965a9da74abcd5 18776 libgpg-error_1.47-3build2.1.debian.tar.xz
Files:
 58e054ca192a77226c4822bbee1b7fdb 1020862 libgpg-error_1.47.orig.tar.bz2
 4a8886f8fd54bd4969dccf994f3909ca 228 libgpg-error_1.47.orig.tar.bz2.asc
 2df4edce4d17e5c64781b6cfa3ddac45 18776 libgpg-error_1.47-3build2.1.debian.tar.xz
Original-Maintainer: Debian GnuPG Maintainers <pkg-gnupg-maint@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEVovyKmYzfL/Jprm3LIPbyOm9DjcFAmb+Ib0ACgkQLIPbyOm9
DjdxXxAAjmI6D/1lUdsPOW2wcrpuRCUaen0uZ84c0dMtSZJWlyZWfL5HGJSN0+gs
BU3ZsmOdu72BJNsz0pVZ4Yl1AdSaWzd9PgyJUklEdkqIX/Mu8tdxMd6hZJFPKIIG
J9lp4jwaUun82I2QbArJhTJtx9n1MWVJJ/ckGnduTWMji9oVGxq29t80rcjYwlPs
AbudzSxGJELGc1OoCecdcHZkQCftalO4x+sIzPMDuVWbN4zWKsF4ZjJmWMDRJBHu
FqMhdXN+vpxqs87ykaKbv/FcmQm1jdUF3vN4Foh7S8zWfPyg+Cbb5klcSSbMzb1b
gkz+r/KSgJYQ4LZ2Ec5UW0jsx9WAF3nrUfFgdjx7iC4wgxOiXZryN04TYpBXxjW+
ZqfwMa7cl0+OAP2fUM0yHbh05lzTxljP9Nt7yPa+NE1qvVUDZxKKk786CuJAHS/V
N0Pf9zZRaZ8XNy+AGHk4IVYxG6h5fBIYHcS+IBkRaZ9PDZg20lm0VT6qvjvYXmfH
4agwjL57Mlu4g1HdXpLARUFtaGTyFqMCKmAq3kSCyk7mQzd2CLojTNbv1oB6rMEq
FR+8C0WuKqdfbYLDlorL3x9bDfhPIThFDiYDzX2ryUrBMt3AD0ggcU6O/L+WShYi
0NERvSGBVf3/HRSGZABHGK4Fo59JeXeCsreRa+xvt0e7U4Vksvo=
=VYfj
-----END PGP SIGNATURE-----
