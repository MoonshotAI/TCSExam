-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: audit
Binary: auditd, libauparse0t64, libauparse-dev, libaudit1, libaudit-common, libaudit-dev, python3-audit, golang-redhat-audit-dev, audispd-plugins
Architecture: linux-any all
Version: 1:3.1.2-2.1build1.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Homepage: https://people.redhat.com/sgrubb/audit/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/audit
Vcs-Git: https://salsa.debian.org/debian/audit.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, pkg-config, python3-all
Build-Depends: dpkg-dev (>= 1.22.5), debhelper-compat (= 13), dh-python <!nopython>, libcap-ng-dev, libkrb5-dev, libldap2-dev <!pkg.audit.noldap>, libwrap0-dev, linux-libc-dev (>= 5.9~), python3-all-dev:any <!nopython>, libpython3-all-dev <!nopython>, swig
Build-Depends-Indep: golang-any
Package-List:
 audispd-plugins deb admin optional arch=linux-any profile=!pkg.audit.noldap
 auditd deb admin optional arch=linux-any
 golang-redhat-audit-dev deb golang optional arch=all
 libaudit-common deb libs optional arch=all
 libaudit-dev deb libdevel optional arch=linux-any
 libaudit1 deb libs optional arch=linux-any
 libauparse-dev deb libdevel optional arch=linux-any
 libauparse0t64 deb libs optional arch=linux-any
 python3-audit deb python optional arch=linux-any profile=!nopython
Checksums-Sha1:
 45cffb1ded9a57a79b33547f58228131d3eb14a6 1219860 audit_3.1.2.orig.tar.gz
 e019798c132265d21f2f8569e8e99e065fd0255a 18860 audit_3.1.2-2.1build1.1.debian.tar.xz
Checksums-Sha256:
 c0b1792d1f0a88c6f1828710509cbb987059fc68712c97669ca90eae103d287d 1219860 audit_3.1.2.orig.tar.gz
 ed9d8bb3ff1194b6c8943c7768596383f995b1d45dbc57b8f5ca5868a7b22558 18860 audit_3.1.2-2.1build1.1.debian.tar.xz
Files:
 9d325b543f79b20a8f7ff2021ebac0c3 1219860 audit_3.1.2.orig.tar.gz
 9f1fe1d823667632f9f7739882c705f7 18860 audit_3.1.2-2.1build1.1.debian.tar.xz
Original-Maintainer: Laurent Bigonville <bigon@debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEVovyKmYzfL/Jprm3LIPbyOm9DjcFAmb+IawACgkQLIPbyOm9
DjeHvA//TXGtI1c5v9OBYPgP5Ps7oiJmi0WzsmUehFNA3rMcChKVDGLknT3WmByk
Lmu/2w0aUF23wnvTNqikTCWUpFdWKlovifZ9o3BGCHyLf8712bzQCAFoImVvZzAd
dvMGn0LzOYtil34Eih+MqEuRP2W5oklnE8wZO6aC5D1sRd0ukz20EIV9RHkLmKeP
YEgklkClkny+lkko/UP308omzN+VspDq7GXFXQXg3APW2d5KpeibH3axwCVlYG+g
3eWnkVFyrLBkpnB7NgBYU1x5L28ZulEUBR6jLDc3TdTyT3ODb+l1QXrxHypgjJUF
EpQKTQAUHq+Nglku7GtoSMjdQJTzzA9BERioq8SO4H9O+MfhYD+lkpFqn40nqWYx
PcpLT1OSbiUsCjDXC2Q3srwAgnIleSiLHyCxHe1TyLLFsBh7nTHoffcJeMsz13k4
znBBm6yDkijzI1+9sk5QKmvyYSMlhh1kH+WJXTjzIGFPWLk6NnXR16r2neDZUsUL
23FRwDdYI2ha0M/AkGU1tqWNMP5YwsqAKcbUfytav/BNBOfCxDbx/qQPu7KICosZ
wSXMvWgR/+Roq7AaOHkqtz0nmQ1xIJniAQ0ZjByzW6SEfOSyDL7nLk1C9y3eSjVh
lO6788dwLEmlsATIAIdcVp2DhCbTQOl6WPEud4cuS0Xuz7jsMzU=
=67FQ
-----END PGP SIGNATURE-----
