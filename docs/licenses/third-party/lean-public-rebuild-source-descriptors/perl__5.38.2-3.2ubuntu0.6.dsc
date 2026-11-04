-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: perl
Binary: perl-base, perl-doc, perl-debug, libperl5.38t64, libperl-dev, perl-modules-5.38, perl
Architecture: any all
Version: 5.38.2-3.2ubuntu0.6
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
 7d9eefa4a52427329d696b9366fe371cc8a22d3f 184740 perl_5.38.2-3.2ubuntu0.6.debian.tar.xz
Checksums-Sha256:
 4d1b34cc058f9963cb89785ecc040d57f6d7725cd83329cfa4ef8b27566454d2 418808 perl_5.38.2.orig-regen-configure.tar.xz
 d91115e90b896520e83d4de6b52f8254ef2b70a8d545ffab33200ea9f1cf29e8 13679524 perl_5.38.2.orig.tar.xz
 5c94f7708145fbe1ca97233c5c83c2bb70c6875013fc17ac50137ec735242bb7 184740 perl_5.38.2-3.2ubuntu0.6.debian.tar.xz
Files:
 139d4ab28a90409790d01ec7a38b6858 418808 perl_5.38.2.orig-regen-configure.tar.xz
 d3957d75042918a23ec0abac4a2b7e0a 13679524 perl_5.38.2.orig.tar.xz
 1aea62b621aeb1707208405e3390f520 184740 perl_5.38.2-3.2ubuntu0.6.debian.tar.xz
Original-Maintainer: Niko Tyni <ntyni@debian.org>

-----BEGIN PGP SIGNATURE-----

iQJUBAEBCgA+FiEEX6QyiBCwMhrhrX3Dv6T2hRCB8x0FAmqpZoQgHHNoYWZheWF0
Lm1hanVtZGVyQGNhbm9uaWNhbC5jb20ACgkQv6T2hRCB8x1uaRAAvh/XsBJTQdc/
lHherdUOus6wbL+NwuiJNqi39oNA+PHyBTzODEIxbUd9fFHR3ozgWx9dQgHxWgVy
JVSCYJ1W3j2+bCXjX3r2XvLAoeuMkz2ubrivj7PX8MZE0wuHDjpbyecsNK8F3IFQ
NWumnpJC57Ekf6/in0agHu1re3ZHP068XC7DBbCQfZXDzEMDZcM6ZJcZKrXdN+Ra
yPmH/K69XwCdaWi6uJuUDlKJ8tXhW0qt4ywiF2gbypTr2uXD8LJWyFxuSdvtm1pe
LSTxluMJU8HQ8RTe0oo6YNgXwDHOXPzIK6h82fghV8YajTx2TRN3Vb+bIj0cVhlB
MyaQO5sfR7mubDBCL6XWLvRovZUv7+huYwtWtuvi480PEm+J65lQGTQDutWeODqJ
KMyhBGLwfdQZAZtua4SqGgImaL+PyWEC0NDb8oDFr4mUqEODd72WprhnCZDQH7ig
bQb+TcssuhYyDQ/6jOzHBLnMRltlb3OdFXHiU5PJ926VYkZbOakTIAS1480zMZks
AWBP9Gv9dVj4gpgCQJ9KudFPFe9Fh2Au8ZvQvzzv+7skoRNmbgJSnReYvTkBgQcF
BlhLdB4Zc5rd/qP2pKUsy/nlVljfKPFt1EM3CcE7AUCWePtrg6ZH7a6i7j8YPyTk
TT0AzZKH5SqN8A8o8aIWN2uhvdnjw6g=
=CfQ0
-----END PGP SIGNATURE-----
