-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: perl
Binary: perl-base, perl-doc, perl-debug, libperl5.38t64, libperl-dev, perl-modules-5.38, perl
Architecture: any all
Version: 5.38.2-3.2ubuntu0.2
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
 66d6f12a466313affaba877f5b35fb37681efe38 171736 perl_5.38.2-3.2ubuntu0.2.debian.tar.xz
Checksums-Sha256:
 4d1b34cc058f9963cb89785ecc040d57f6d7725cd83329cfa4ef8b27566454d2 418808 perl_5.38.2.orig-regen-configure.tar.xz
 d91115e90b896520e83d4de6b52f8254ef2b70a8d545ffab33200ea9f1cf29e8 13679524 perl_5.38.2.orig.tar.xz
 f7149a24aef35ff716fe9e6c724f8f9a769d1c77cddd6db301b7b7c450989b75 171736 perl_5.38.2-3.2ubuntu0.2.debian.tar.xz
Files:
 139d4ab28a90409790d01ec7a38b6858 418808 perl_5.38.2.orig-regen-configure.tar.xz
 d3957d75042918a23ec0abac4a2b7e0a 13679524 perl_5.38.2.orig.tar.xz
 9ca53735dbbcb4e41e8d5f34421bdcb4 171736 perl_5.38.2-3.2ubuntu0.2.debian.tar.xz
Original-Maintainer: Niko Tyni <ntyni@debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmiE+7IACgkQZWnYVadE
vpO27A/+O+ZfuXiiGymcPZgs2puYYaCHL6hQOHYkjjSsfWSji2UbU1fymY8VT9eI
WXfVdHsPHV3LzF0IHDMbLmFQgraePOw+A32HvLg/iO8RGnuYE1EK+luBMa/2rnUX
HOba5vioG5PmYLM2vMaj/tbuSdzmBjVius+KGzbOvPpc6o4A7H2nriYlVyIxR18U
7xWiWaX/u6HRbYOQQAWbtwqFpO0BI9H3TxIGw6h2xREXa7u7h9KlHDzziJpPgmNn
TRBp58AT6peWhJytvBIAbmBsGGgCel64nbw9UZj97s5A6874bdOarWRZQ8WruRXP
BrmeoYBiLUw9t5dFcj+DM4lRUTgkC7NTwQr2ZY33CKtCMdtTQFAA4AI9pFwp0VRC
ed+z0MwYfMvIDyFGLfX86ah6C5hWSNV0yAhZRV2YdYuE7x8KYTcpgJzmznTLbIg7
WAq9WcVpRhbXI7RTr6SU2pyimrhbNiVwL+AgYoB6c0wvkce7hrqw51zAM1Zh0M0A
rKtG19Y2CKV6cr51LjIIeZdfTeiB8cvQnW9Rxfmg6PkWvDkc1Kez03leTQAgYVUi
kjWuGod7cfSSMojNTX1Qyj1X5fmyMSXMkJYK7s6NNqhdEo15oRqkMCM9IOa8FGV/
TDKxuo4/OOEa1EllOecR0PW2gKunBCdanRWwTPDP5R3ufY9cvNc=
=aJ99
-----END PGP SIGNATURE-----
