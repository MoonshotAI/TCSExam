-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: openldap
Binary: slapd, slapd-contrib, slapd-smbk5pwd, ldap-utils, libldap2, libldap-common, libldap-dev, libldap2-dev, slapi-dev
Architecture: any all
Version: 2.6.10+dfsg-0ubuntu0.24.04.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Steve Langasek <vorlon@debian.org>, Torsten Landschoff <torsten@debian.org>, Ryan Tandy <ryan@nardis.ca>, Sergio Durigan Junior <sergiodj@debian.org>
Homepage: https://www.openldap.org/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/openldap-team/openldap
Vcs-Git: https://salsa.debian.org/openldap-team/openldap.git
Testsuite: autopkgtest
Testsuite-Triggers: heimdal-kdc, openssl, python3-passlib, samba, schema2ldif, ssl-cert
Build-Depends: debhelper-compat (= 13), dh-apparmor, dpkg-dev (>= 1.17.14), groff-base, heimdal-multidev (>= 7.4.0.dfsg.1-1~) <!pkg.openldap.noslapd>, libargon2-dev <!pkg.openldap.noslapd>, libcrack2-dev <!pkg.openldap.noslapd>, libgnutls28-dev, libltdl-dev <!pkg.openldap.noslapd>, libperl-dev (>= 5.8.0) <!pkg.openldap.noslapd>, libsasl2-dev, libwrap0-dev <!pkg.openldap.noslapd>, nettle-dev <!pkg.openldap.noslapd>, openssl <!nocheck>, perl:any, pkg-config (>= 0.29), po-debconf, unixodbc-dev <!pkg.openldap.noslapd>, krb5-admin-server <!nocheck>, krb5-user <!nocheck>, krb5-kdc <!nocheck>, libsasl2-modules-gssapi-mit <!nocheck>, sasl2-bin <!nocheck>
Build-Conflicts: autoconf2.13, bind-dev, libbind-dev
Package-List:
 ldap-utils deb net optional arch=any
 libldap-common deb libs optional arch=all
 libldap-dev deb libdevel optional arch=any
 libldap2 deb libs optional arch=any
 libldap2-dev deb oldlibs optional arch=all
 slapd deb net optional arch=any profile=!pkg.openldap.noslapd
 slapd-contrib deb net optional arch=any profile=!pkg.openldap.noslapd
 slapd-smbk5pwd deb oldlibs optional arch=all profile=!pkg.openldap.noslapd
 slapi-dev deb libdevel optional arch=any profile=!pkg.openldap.noslapd
Checksums-Sha1:
 fedb1576cd4dcfe9838d6ac4b00592698a97b086 3754560 openldap_2.6.10+dfsg.orig.tar.xz
 b894272f2698235b3fa76132a5d58a0fccd2544a 191132 openldap_2.6.10+dfsg-0ubuntu0.24.04.1.debian.tar.xz
Checksums-Sha256:
 e871102bda1e42155fd4d6be4825a297e1c593cb0907b84fc7dde888dc847877 3754560 openldap_2.6.10+dfsg.orig.tar.xz
 91bdd643954645ce8ba51152516831ce4dcb497a222b88a5df847c4780e5f79e 191132 openldap_2.6.10+dfsg-0ubuntu0.24.04.1.debian.tar.xz
Files:
 4cd7308803ad2c7eb3168be97e76ccf6 3754560 openldap_2.6.10+dfsg.orig.tar.xz
 1f50bfc6f4959b1442b4eacd2ec4bdfb 191132 openldap_2.6.10+dfsg-0ubuntu0.24.04.1.debian.tar.xz
Original-Maintainer: Debian OpenLDAP Maintainers <pkg-openldap-devel@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

wsG7BAEBCgBvBYJpNylGCRCsmD61v2vLqUcUAAAAAAAeACBzYWx0QG5vdGF0aW9u
cy5zZXF1b2lhLXBncC5vcmdsjnBrPkhkUcH3Ae2kCZ2UR8Op+2hQedbTE+WLU4TE
WhYhBIhmQdY1jNpGpWwccqyYPrW/a8upAACGRw/8D0L202QaUFP2ODL5ZeNImLU2
WmByNo3wdqOd97M7iAm7SxqOXxm8gX95QXBNpItA7E45Cdix+X0SvPt0BLID5miF
+V4OHQ89FUXSfuA4XxV+kp/cR3IfmcXd7+8Ybp0dN2s/V4BiWi+4NON9lQ0UV/YG
WAn5jUWF6Go2Y8MRsW6SYujeNS3WpHmV3THDUZwB+2/0XP4FLGGjq6i4QxvX3oYu
fHn4+w9f/txx0xMd3nv+VCtN5i+eLbNxo1lZL5U4c02M6uHCmWkRZIEatRqatPkz
2B8yOAUVof9EeRzTJT+KpbWb5hWq2EpcSuMX4jl14cW3qZuIgSwKfJNuAxK6rMAb
ndw5JvS8sjcN93S21NBkighsSMATexVRpAU3yGWVPCFoVftTaVpZfyHcD9Z+MAy1
yp8rAvZHx2TTrPz8ZwQLPNACXzr8mAhNId+JAkCF9oYgMtoKICYbIJk/QFKR81Vd
i58U/8FNb/TXanR1HupdVvApZvn72KCTwIptPm6UDnICUEz0Wg5YrMUsxteN22Be
cMPij/TDGuMR5IMs4kL8PwtJtZW2+pQx5jw8yGxtxjx/Y4rJC99J9dBW6aUzd0js
NCNh9HT8zkoH7xhyowFfo4XWhkgMylNYdMbT2IiVvcw+FNVUjJLtRQdBI4bffmEd
R+i0GWhr6+UvcT0e4Ro=
=fNqx
-----END PGP SIGNATURE-----
