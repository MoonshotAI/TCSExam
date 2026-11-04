-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA384

Format: 3.0 (quilt)
Source: perl
Binary: perl-base, perl-doc, perl-debug, libperl5.40, libperl-dev, perl-modules-5.40, perl
Architecture: any all
Version: 5.40.1-6
Maintainer: Niko Tyni <ntyni@debian.org>
Uploaders: Dominic Hargreaves <dom@earth.li>
Homepage: https://dev.perl.org/perl5/
Standards-Version: 3.9.8
Vcs-Browser: https://salsa.debian.org/perl-team/interpreter/perl
Vcs-Git: https://salsa.debian.org/perl-team/interpreter/perl.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, cpio, db-util, dist, dpkg-dev, gdbmtool, libapt-pkg-perl, libdpkg-perl, pkg-perl-autopkgtest
Build-Depends: file, cpio, dpkg-dev (>= 1.22.5), libcrypt-dev, libdb-dev, libgdbm-dev (>= 1.18-3), libgdbm-compat-dev, netbase <!nocheck>, procps [!hurd-any] <!nocheck>, debhelper-compat (= 13), zlib1g-dev | libz-dev, libbz2-dev, dist (>= 3.5-236), libc6-dev (>= 2.37-8) [ppc64el], libc6-dev (>= 2.19-9) [s390x]
Package-List:
 libperl-dev deb libdevel optional arch=any
 libperl5.40 deb libs optional arch=any
 perl deb perl standard arch=any
 perl-base deb perl required arch=any essential=yes
 perl-debug deb devel optional arch=any
 perl-doc deb doc optional arch=all
 perl-modules-5.40 deb libs optional arch=all
Checksums-Sha1:
 82d1edc45031c917619d2c412c6d5c34a50fde0a 421056 perl_5.40.1.orig-regen-configure.tar.xz
 4ffe5246c791df884363aed05ba81ba41cb02084 13930924 perl_5.40.1.orig.tar.xz
 291c163659c638fb44479a1250f04348e63c8683 172892 perl_5.40.1-6.debian.tar.xz
Checksums-Sha256:
 4ea023d08101443f6ed9dc3bdd9bb5f5e08087678dc9e443d195df22da36209a 421056 perl_5.40.1.orig-regen-configure.tar.xz
 dfa20c2eef2b4af133525610bbb65dd13777ecf998c9c5b1ccf0d308e732ee3f 13930924 perl_5.40.1.orig.tar.xz
 3071cd0d0ddb2bc58a739d331c5e8c5b549f679714b7d8f698b7f8f7ab27b3a3 172892 perl_5.40.1-6.debian.tar.xz
Files:
 9b3f5231e0354423504e64e80b0a8be6 421056 perl_5.40.1.orig-regen-configure.tar.xz
 bab3547a5cdf2302ee0396419d74a42e 13930924 perl_5.40.1.orig.tar.xz
 2d7afd2806329c5aba18ab5347b26b60 172892 perl_5.40.1-6.debian.tar.xz

-----BEGIN PGP SIGNATURE-----

iKcEARMJAC8WIQTuZv2Xfg2x/uVxefeK/rNkDrE5sgUCaIfkMBEcbnR5bmlAZGVi
aWFuLm9yZwAKCRCK/rNkDrE5siIqAYCMOuj5x2yOoBvQfvRJwY0zp97Xc4nslWeQ
N4/ENLb/RIQ8RmoMfUUh6Uy4mdvbG4ABf11QQNTr38ihIqGceAYExL8Fc7SsL5km
aWvVOvxIWE2Da1qlVIs3VN5mDShEd5j5ag==
=zKY3
-----END PGP SIGNATURE-----
