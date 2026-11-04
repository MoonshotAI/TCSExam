-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: krb5
Binary: krb5-user, krb5-kdc, krb5-kdc-ldap, krb5-admin-server, krb5-kpropd, krb5-multidev, libkrb5-dev, libkrb5-dbg, krb5-pkinit, krb5-otp, krb5-k5tls, krb5-doc, libkrb5-3, libgssapi-krb5-2, libgssrpc4t64, libkadm5srv-mit12, libkadm5clnt-mit12, libk5crypto3, libkdb5-10t64, libkrb5support0, libkrad0, krb5-gss-samples, krb5-locales, libkrad-dev
Architecture: any all
Version: 1.20.1-6ubuntu2.7
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Russ Allbery <rra@debian.org>, Benjamin Kaduk <kaduk@mit.edu>
Homepage: https://web.mit.edu/kerberos/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/krb5
Vcs-Git: https://salsa.debian.org/debian/krb5
Testsuite: autopkgtest
Testsuite-Triggers: ldap-utils, libsasl2-modules-gssapi-mit, slapd
Build-Depends: dpkg-dev (>= 1.22.5), byacc | bison, comerr-dev, debhelper-compat (= 13), docbook-to-man, libkeyutils-dev [linux-any], libldap2-dev <!stage1>, libsasl2-dev <!stage1>, libssl-dev, libverto-dev (>= 0.2.4), pkg-config, ss-dev
Build-Depends-Arch: dpkg-dev (>= 1.22.5), keyutils [linux-any] <!nocheck>, libcmocka-dev <!nocheck>, python3-kdcproxy <!nocheck>, python3-pyrad <!nocheck>
Build-Depends-Indep: doxygen, doxygen-latex, python3, python3-cheetah, python3-lxml, python3-sphinx, tex-gyre
Package-List:
 krb5-admin-server deb net optional arch=any
 krb5-doc deb doc optional arch=all
 krb5-gss-samples deb net optional arch=any
 krb5-k5tls deb net optional arch=any
 krb5-kdc deb net optional arch=any
 krb5-kdc-ldap deb net optional arch=any profile=!stage1
 krb5-kpropd deb net optional arch=any
 krb5-locales deb localization optional arch=all
 krb5-multidev deb libdevel optional arch=any
 krb5-otp deb net optional arch=any
 krb5-pkinit deb net optional arch=any
 krb5-user deb net optional arch=any
 libgssapi-krb5-2 deb libs optional arch=any
 libgssrpc4t64 deb libs optional arch=any
 libk5crypto3 deb libs optional arch=any
 libkadm5clnt-mit12 deb libs optional arch=any
 libkadm5srv-mit12 deb libs optional arch=any
 libkdb5-10t64 deb libs optional arch=any
 libkrad-dev deb libdevel optional arch=any
 libkrad0 deb libs optional arch=any
 libkrb5-3 deb libs optional arch=any
 libkrb5-dbg deb debug optional arch=any
 libkrb5-dev deb libdevel optional arch=any
 libkrb5support0 deb libs optional arch=any
Checksums-Sha1:
 06278439a6cd5a2aa861d8e877451b794487534b 8661660 krb5_1.20.1.orig.tar.gz
 1cd01998135e3db3c4401b84459fb19ab8baabaf 833 krb5_1.20.1.orig.tar.gz.asc
 e53fff99faa04999c71f571977e639b9da75a073 123356 krb5_1.20.1-6ubuntu2.7.debian.tar.xz
Checksums-Sha256:
 704aed49b19eb5a7178b34b2873620ec299db08752d6a8574f95d41879ab8851 8661660 krb5_1.20.1.orig.tar.gz
 2afeec5dbc586cc40b7975645e02b4c41c4d719dd02213e828c72d8239d55666 833 krb5_1.20.1.orig.tar.gz.asc
 cc472330a59122badf2bd00e6f14f05db070bf8cdb28cc77e108c1c32d038d90 123356 krb5_1.20.1-6ubuntu2.7.debian.tar.xz
Files:
 73f5780e7b587ccd8b8cfc10c965a686 8661660 krb5_1.20.1.orig.tar.gz
 46551f0a032aa02dccac3789a344e028 833 krb5_1.20.1.orig.tar.gz.asc
 66a2c4b49d35cf0359c839986de15964 123356 krb5_1.20.1-6ubuntu2.7.debian.tar.xz
Original-Maintainer: Sam Hartman <hartmans@debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmpX7uEACgkQZWnYVadE
vpNX8BAAuTsZdJR5T3jMxaqNFON7CNQhSbFEHzIG3UgJXOiWr+iLi+GXkOpCOpNl
ssuS+KrqmgAEPq6oZwwwgevDoyP+uFFPXNUpSugQPYf6HtXnWZLyZ45GRR3s+rJL
FciHb4FtMj+SaEmTeGUswnKmTI2lUKmgC4ZXN6+5iL/b4cGqATIWfANtxuwqpz5l
tl5QsZ6WEV0sQK/ysZFxCFxFWwna3FDasN9tcM22prCbeDNT+lvxR4Mgbm/D3Tuo
HP1XwTAK5vsCtvistIdJpIfafXgKcxz99VZVv768sKoNaIFov/7LWbGvRheVPIpJ
OneoxHpfb9qTqYgnxt6qVmfm8d+D4Y0t7KO6ZfKRag4LibKOm54Y9X878/eOM1VD
hK7ZQk9DMkOrfRZXnfZ/7fPYV8OtxKB2p4SXRVBVBCrzu5QDa+6gyQ02ocprHkZ8
oYt7e1qTJaEcqeQmKyu/F3NTqP+Zp3+h/5CtzUrfduq0Th64bwq/6q9OvJz+0vAp
I8C4A/7nKdKkWGQXo5GaMNgpfO3mSBM3P0UDhgnZlSeCNGbc9fV6GwBCz3P5WVcY
sO9ucDZQtEHy5Glni3qlF0kx1iLhXbZBGJ8pHQqXyT51hPRkrmTMRRrEsvhJlC64
HFh+RFjqDa0+KlpejlzSEV7iNhfovBbOBCq7anIFjsoAwVPLuyg=
=Lc9W
-----END PGP SIGNATURE-----
