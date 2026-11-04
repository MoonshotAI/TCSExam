-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: perl
Binary: perl-base, perl-doc, perl-debug, libperl5.38t64, libperl-dev, perl-modules-5.38, perl
Architecture: any all
Version: 5.38.2-3.2ubuntu0.3
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Dominic Hargreaves <dom@earth.li>
Homepage: http://dev.perl.org/perl5/
Standards-Version: 3.9.8
Vcs-Browser: https://salsa.debian.org/perl-team/interpreter/perl
Vcs-Git: https://salsa.debian.org/perl-team/interpreter/perl.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, cpio, db-util, dist, dpkg-dev, gdbmtool, libapt-pkg-perl, libdpkg-perl, pkg-perl-autopkgtest
Build-Depends: file, cpio, dpkg-dev (>= 1.22.5), libcrypt-dev, libdb-dev, libgdbm-dev (>= 1.18-3), libgdbm-compat-dev, netbase <!nocheck>, procps [!hurd-any] <!nocheck>, debhelper-compat (= 13), zlib1g-dev | libz-dev, libbz2-dev, dist (>= 3.5-236), libc6-dev (>= 2.37-8) [ppc64el], libc6-dev (>= 2.19-9) [s390x]
Package-List:
 libperl-dev deb libdevel optional arch=any
 libperl5.38t64 deb libs optional arch=any
 perl deb perl standard arch=any
 perl-base deb perl required arch=any essential=yes
 perl-debug deb devel optional arch=any
 perl-doc deb doc optional arch=all
 perl-modules-5.38 deb libs optional arch=all
Checksums-Sha1:
 0b5d76399e77b21ce892cd38f4a63703628ce896 418808 perl_5.38.2.orig-regen-configure.tar.xz
 af1d5f9e0499f3cfa4736433631aebf7624714da 13679524 perl_5.38.2.orig.tar.xz
 d6aca7f559e2e972bf1bd3c7ef2476181f21e6d0 173452 perl_5.38.2-3.2ubuntu0.3.debian.tar.xz
Checksums-Sha256:
 4d1b34cc058f9963cb89785ecc040d57f6d7725cd83329cfa4ef8b27566454d2 418808 perl_5.38.2.orig-regen-configure.tar.xz
 d91115e90b896520e83d4de6b52f8254ef2b70a8d545ffab33200ea9f1cf29e8 13679524 perl_5.38.2.orig.tar.xz
 46e7bbb90405eac649fbc1822adf3a29616d3b09f8583359e3a1537dc0959fec 173452 perl_5.38.2-3.2ubuntu0.3.debian.tar.xz
Files:
 139d4ab28a90409790d01ec7a38b6858 418808 perl_5.38.2.orig-regen-configure.tar.xz
 d3957d75042918a23ec0abac4a2b7e0a 13679524 perl_5.38.2.orig.tar.xz
 d0742ad9cc63431a687ff081076b2b2c 173452 perl_5.38.2-3.2ubuntu0.3.debian.tar.xz
Original-Maintainer: Niko Tyni <ntyni@debian.org>

-----BEGIN PGP SIGNATURE-----

iQHTBAEBCgA9FiEE26yozGlLvY8PLmS9C+du+fOjiEwFAmo5QoMfHGNocmlzYS5v
aWtvbm9tb3VAY2Fub25pY2FsLmNvbQAKCRAL527586OITPifC/4zx0wwlTAlc/TO
JuMyf8T/vzFYI/aSUvvLQwoqzd55ub7CM/Es+A8JsgqeBzaTwHasF0pRYe/PhUTL
5zfuBeOCLy/vrzJiKf4H605JU8Sc2AMRevEJd0rROidRA2TNliHDf/jkU9pVG/aH
HCcpdjbZ/3niAq+ZtUJ+eMhmZ/1OWch2tklQUwHyLq9UZRlfwxP5pjhMTDDdgT/s
kJ7YUN7Gk9+UKMS32AU8JhCDGhRHh54jsNAzMJCp/7xi+G5Twlh3EoLz3QXmyHrj
1az/tk4zCrlt9XUXZQY4N8gK8ONsuFf/sPIVkJtLGHf1rJmBG660isA0oAi0WMvu
MGmUTrzTDzv09ibE7HzejI5ZhonuGxqZ4lPmzhTBlCyKNEzpC4bk4jwiJ7s2iB+m
nDT0hjE1LLYgaFz/ami1EU4os92pDac96aacHLvgBTaSnuU2dOsjHoTCWJK9RCsv
hmsMpC/nSmA5NFQN3OmOv35JoF5KS9Y3zNjkOPNKJ7phSTanZ1k=
=KRy/
-----END PGP SIGNATURE-----
