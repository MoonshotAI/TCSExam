-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: krb5
Binary: krb5-user, krb5-kdc, krb5-kdc-ldap, krb5-admin-server, krb5-kpropd, krb5-multidev, libkrb5-dev, libkrb5-dbg, krb5-pkinit, krb5-otp, krb5-k5tls, krb5-doc, libkrb5-3, libgssapi-krb5-2, libgssrpc4t64, libkadm5srv-mit12, libkadm5clnt-mit12, libk5crypto3, libkdb5-10t64, libkrb5support0, libkrad0, krb5-gss-samples, krb5-locales, libkrad-dev
Architecture: any all
Version: 1.20.1-6ubuntu2.10
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
 krb5-kdc-ldap deb net optional arch=any profile=!stage1 profile:v1=!stage1
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
 56bc0eafd299227877dbba375de0f605633d50cd 132764 krb5_1.20.1-6ubuntu2.10.debian.tar.xz
Checksums-Sha256:
 704aed49b19eb5a7178b34b2873620ec299db08752d6a8574f95d41879ab8851 8661660 krb5_1.20.1.orig.tar.gz
 e3a9136f4c3d93f41b5ffb3533ff472fedf52efecebaba79127fbc1fbdced6ca 132764 krb5_1.20.1-6ubuntu2.10.debian.tar.xz
Files:
 73f5780e7b587ccd8b8cfc10c965a686 8661660 krb5_1.20.1.orig.tar.gz
 e2f1298d13c215eea5f2aa3f58e682f9 132764 krb5_1.20.1-6ubuntu2.10.debian.tar.xz
Original-Maintainer: Sam Hartman <hartmans@debian.org>

-----BEGIN PGP SIGNATURE-----

iQJFBAEBCgAvFiEEQ5iE5oYqQpwpDfY7AzxMonYCSDQFAmqMbpcRHGF0aG9zQHVi
dW50dS5jb20ACgkQAzxMonYCSDQ3fRAAoUB/JWFWsJGc49LwzoolfPd8eQAshE5v
zj52R9EqWl9BcU+KkGMUrk/5LmH/9NkP6xIj/7ZvEgweqLBCGrvfr5dEE1/5DLtM
rCl8sq7C9Ma9q7Hm0C/igHnbv4VDR6oTEYNQQtEiWwtuXdKY9lWJJC+sYn95lFgj
oeqN7/Q6k2bjob7p+0gaFHrCLama6rwDcT7m8t/WgtdV24wTqKeSZhlK7IUTt787
UCINtsy/iq0aH+mHyF6h3jtqO6oq54W6AezCPe04WH8+TfVWJ1Hf6B8n6OpB4vh9
U9buYmiGEhoeMWzZbSTHkjIYZw0HlS5I93SR2rjvSVldWif7KaMIBF2/E8MSFK3W
P09cjTFnd0imebUcSsY+ffkVFEdVf1rDYXXM5HijoNetUUBeBo797oWJe+aLsoIZ
9UQIrGC40PQxLf5XNdGalO0Gm10hjpRDhs81r9WCPAnSvKaQzY1JiL1E4HN0j6/B
AQWGm7ybKiS4YwOUeA9gtvHHbKAfEJaI35xkiGEoDh/AzV+lROCOip7s8y03RVji
O2GtMlyB1bpy+a8L+gwgcEz1Ln04BGQDshtkh5gP7roPYS/qnDXIY/Zj67V5nzkj
DUqdmA2Dnk4CVy0A07thYK8rEsBhoGT/ffuuPOWOD/CeVD8ah/Cz+lUfoog69SIp
HAE147PVY3w=
=+//l
-----END PGP SIGNATURE-----
