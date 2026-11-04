-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: gnutls28
Binary: libgnutls28-dev, libgnutls30t64, gnutls-bin, gnutls-doc, libgnutls-openssl27t64, libgnutls-dane0t64
Architecture: any all
Version: 3.8.3-1.1ubuntu3.6
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders:  Andreas Metzler <ametzler@debian.org>, Eric Dorland <eric@debian.org>, James Westby <jw+debian@jameswestby.net>, Simon Josefsson <simon@josefsson.org>,
Homepage: https://www.gnutls.org/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/gnutls-team/gnutls
Vcs-Git: https://salsa.debian.org/gnutls-team/gnutls.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, ca-certificates, datefudge, freebsd-net-tools, net-tools, openssl, softhsm2
Build-Depends: dpkg-dev (>= 1.22.5), bison, ca-certificates <!nocheck>, chrpath, datefudge <!nocheck>, debhelper-compat (= 13), freebsd-net-tools [kfreebsd-i386 kfreebsd-amd64] <!nocheck>, gperf, libcmocka-dev <!nocheck>, libidn2-dev, libp11-kit-dev, libssl-dev <!nocheck>, libtasn1-6-dev, libunbound-dev, libunistring-dev, net-tools [!kfreebsd-i386 !kfreebsd-amd64] <!nocheck>, nettle-dev (>= 3.6), openssl <!nocheck>, pkg-config, python3:any, softhsm2 <!nocheck>
Build-Depends-Indep: gtk-doc-tools, texinfo, texlive-latex-base, texlive-plain-generic
Build-Conflicts: libgnutls-dev
Package-List:
 gnutls-bin deb net optional arch=any
 gnutls-doc deb doc optional arch=all
 libgnutls-dane0t64 deb libs optional arch=any
 libgnutls-openssl27t64 deb libs optional arch=any
 libgnutls28-dev deb libdevel optional arch=any
 libgnutls30t64 deb libs optional arch=any
Checksums-Sha1:
 806156ac9563caab642d6274496b9cc5b2117612 6463720 gnutls28_3.8.3.orig.tar.xz
 e256237d54d45e4b6f46fe692651d6dea33f359c 854 gnutls28_3.8.3.orig.tar.xz.asc
 01173663ede477f62a743d3b4a3d5489c0e54857 124984 gnutls28_3.8.3-1.1ubuntu3.6.debian.tar.xz
Checksums-Sha256:
 f74fc5954b27d4ec6dfbb11dea987888b5b124289a3703afcada0ee520f4173e 6463720 gnutls28_3.8.3.orig.tar.xz
 b2b90d225728890b0e2aa7c05e5f25f8ba1282821b46e72cd99f0c732b639cef 854 gnutls28_3.8.3.orig.tar.xz.asc
 b4cc6ebad4cb21ffe82d094f6d9c90de31e08a8b31ed36911a2adbe5aaa56d47 124984 gnutls28_3.8.3-1.1ubuntu3.6.debian.tar.xz
Files:
 269966167fa5bf8bae5f7534bcc3c454 6463720 gnutls28_3.8.3.orig.tar.xz
 8da0da357d6762b98a491bf0a3fc6e1f 854 gnutls28_3.8.3.orig.tar.xz.asc
 1a18dd2a82ea30819b6d02009767974a 124984 gnutls28_3.8.3-1.1ubuntu3.6.debian.tar.xz
Original-Maintainer: Debian GnuTLS Maintainers <pkg-gnutls-maint@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmn+NgUACgkQZWnYVadE
vpOCqw/7BAP+F3omPSun9rNxzocOVw8iLNfsf0YrYq20wrUesqHNPeTwSy7w65MJ
a4DAkYmewve7yYmRhvMz+Y6USvEZ9iTHx3Y+hy2iTEMYrvm7zsCeUMJjDrhvzG+3
H074PzoG6Rp2TQlluqEKCJ3RI2JjEGHyj0GDRtrW6yJAADYNyuHXqjRiEAoPfHcW
V96kzWvKDpyVtUQwhFAKsf++obgd30Kle4ZorzVub9XVxhOagNb39RLEKEtxTV9t
448ujGE7fJbYpMNEFYiTS6VAnXrD1RpgBjdfJtzLPE+XsQfxNReIwjAAvsWw9DRy
Eu1GkkwsuH1QMX2yliZ/248DlCGPTgGeNOwcSEw7/iYs9iI3J/DVx7JW+1kgVOPJ
OoBkLSDRdlI5wb2UwZ2vaL9830q4SNdyMy3xMzg6P0pUmpZZfhlfjm3A17ccRfiZ
DrVAQwWyYrHuowqpIGWUCpZ4n9vUD13Sl1T9sPGPugJVpyFqWqBB3R1Ta+futTGz
qtM+Wxu2BCChmzd28XI6ofmtdJaBdF+q7G4qEzH+RpunxfvlCjVa/0D5pTEqRmyT
mbHXjN3UXC4OGbQpbhTU4Dv5z2aclroChmhxrjGUhPgaMXurLtsxE6iSKyQNc2FY
wYCSkC1asyxWYMBtE8XWHx8xafilchiu8gg1MH4LuuMFU9nEE48=
=+67A
-----END PGP SIGNATURE-----
