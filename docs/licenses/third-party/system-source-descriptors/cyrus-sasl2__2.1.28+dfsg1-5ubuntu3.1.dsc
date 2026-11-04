-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: cyrus-sasl2
Binary: sasl2-bin, cyrus-sasl2-doc, libsasl2-2, libsasl2-modules, libsasl2-modules-db, libsasl2-modules-ldap, libsasl2-modules-otp, libsasl2-modules-sql, libsasl2-modules-gssapi-mit, libsasl2-dev, libsasl2-modules-gssapi-heimdal
Architecture: any all
Version: 2.1.28+dfsg1-5ubuntu3.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Ondřej Surý <ondrej@debian.org>,
Homepage: https://www.cyrusimap.org/sasl/
Standards-Version: 4.3.0.1
Vcs-Browser: https://salsa.debian.org/debian/cyrus-sasl2
Vcs-Git: https://salsa.debian.org/debian/cyrus-sasl2.git
Testsuite: autopkgtest
Testsuite-Triggers: krb5-admin-server, krb5-kdc, krb5-user, ldap-utils, slapd
Build-Depends: chrpath, debhelper-compat (= 12), default-libmysqlclient-dev <!pkg.cyrus-sasl2.nosql>, docbook-to-man, groff-base, heimdal-multidev <!pkg.cyrus-sasl2.nogssapi>, krb5-multidev <!pkg.cyrus-sasl2.nogssapi>, libdb-dev, libcrypt-dev, libkrb5-dev <!pkg.cyrus-sasl2.nogssapi>, libldap2-dev <!pkg.cyrus-sasl2.noldap>, libpam0g-dev, libpod-pom-view-restructured-perl:native, libpq-dev <!pkg.cyrus-sasl2.nosql>, libsqlite3-dev, libssl-dev, po-debconf, python3-six, python3-sphinx-rtd-theme:native
Build-Conflicts: heimdal-dev
Package-List:
 cyrus-sasl2-doc deb doc optional arch=all
 libsasl2-2 deb libs optional arch=any
 libsasl2-dev deb libdevel optional arch=any
 libsasl2-modules deb libs optional arch=any
 libsasl2-modules-db deb libs optional arch=any
 libsasl2-modules-gssapi-heimdal deb libs optional arch=any profile=!pkg.cyrus-sasl2.nogssapi
 libsasl2-modules-gssapi-mit deb libs optional arch=any profile=!pkg.cyrus-sasl2.nogssapi
 libsasl2-modules-ldap deb libs optional arch=any profile=!pkg.cyrus-sasl2.noldap
 libsasl2-modules-otp deb libs optional arch=any
 libsasl2-modules-sql deb libs optional arch=any profile=!pkg.cyrus-sasl2.nosql
 sasl2-bin deb utils optional arch=any
Checksums-Sha1:
 297ba17d605b880a9a9beb8b08abc0cf90945c40 794540 cyrus-sasl2_2.1.28+dfsg1.orig.tar.xz
 961c56c7eec5ef4149ab4b294430108f2c54b54b 98324 cyrus-sasl2_2.1.28+dfsg1-5ubuntu3.1.debian.tar.xz
Checksums-Sha256:
 e796a5d85d1a85e1b433d43504e467f9075c7ebc0b45730a3996cf11b1deada4 794540 cyrus-sasl2_2.1.28+dfsg1.orig.tar.xz
 a1017cf9d4fd098325338d1d7f1f71cb87102934e7b35c8f5e726d246360689e 98324 cyrus-sasl2_2.1.28+dfsg1-5ubuntu3.1.debian.tar.xz
Files:
 3ab6f193b23938524b51706616d38ad1 794540 cyrus-sasl2_2.1.28+dfsg1.orig.tar.xz
 89a0aa052ad777382c52e714edc0905d 98324 cyrus-sasl2_2.1.28+dfsg1-5ubuntu3.1.debian.tar.xz
Original-Maintainer: Debian Cyrus Team <team+cyrus@tracker.debian.org>
-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEVovyKmYzfL/Jprm3LIPbyOm9DjcFAma1gmcACgkQLIPbyOm9
Djf1LBAAh558GtTjSCMRhOfULkOFKLfdBMWnluo3Xx3cDL2yCDuo2Up17ChyZvep
KaKe4lcYWvoCf79NLwXlxnlUl6KevugYV3F36PLXXoLrQDDgqPf4RJmydztshKL+
msjpwbKYwE2dDsmI06RdCSjPqJeYGPn0J2qySIWvhypUgkOBqnE9upnqqIiBrow6
Lv1h41U3etFFWie+ODvb3zM1Wwp92CnDvz0ezjKG8Cy/TrjiJ6lyckAUEreDrGDB
dCrIgxuHkEG/EvGseRscpuqbISYx2T+94irXP/7QoqxLPEgkRfRWSZbpPdOVsoCV
TTzx8KSXERnyqlP+0oeTZ+bOlCBJ25z8eYVy2bpcLxvnzbBpnSQySKQplbuywsBy
a0JVrjVV6/+hU69/8+F1KjYoxNJcEyMPbDw6ZCmo1N08bXZqcI7QOSlMMogG+Fxs
BrI41CNFGtWmMOF05/jp10o4fs4tCx118AOexRnzA9j09ezj+3OblXykRlGTX1eR
SidR5a9Th9LeVffJiX/Ckln26UT4YwhO6hDxwbvx9RjxfR7RzvdFXtepw397L+CR
4WC2tGHX+3kVFnOCrZCygGwPr37336FXiazkpeAkhrFfpfNkBkN4JhI7E10hMTmp
YXfRimZqUb15Mabq2CLYujvtmVpnB6+UN+xHmJ6zs07z/DBaB/s=
=HM/S
-----END PGP SIGNATURE-----
