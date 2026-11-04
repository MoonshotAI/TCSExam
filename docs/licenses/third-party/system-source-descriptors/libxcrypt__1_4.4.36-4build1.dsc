-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: libxcrypt
Binary: libcrypt1, libcrypt2, libcrypt-dev, libcrypt1-udeb, libxcrypt-source
Architecture: any all
Version: 1:4.4.36-4build1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Standards-Version: 4.6.2.0
Vcs-Browser: https://salsa.debian.org/md/libxcrypt
Vcs-Git: https://salsa.debian.org/md/libxcrypt.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, pkg-config
Build-Depends: debhelper-compat (= 13), autoconf, automake, libtool, pkg-config
Package-List:
 libcrypt-dev deb libdevel optional arch=any
 libcrypt1 deb libs optional arch=gnu-any-any
 libcrypt1-udeb udeb debian-installer optional arch=gnu-any-any
 libcrypt2 deb libs optional arch=musl-any-any
 libxcrypt-source deb devel optional arch=all
Checksums-Sha1:
 79db48905dc82e907a0a079681c8f98962b8434f 392732 libxcrypt_4.4.36.orig.tar.xz
 9d0aa7b1bc57c21fca1dbe8b5f29f6d5298ea431 8356 libxcrypt_4.4.36-4build1.debian.tar.xz
Checksums-Sha256:
 7b7abbc89f13f5194211aa6861ed954e4fa3a210a4cb64f7e13dc8cf413e7f2a 392732 libxcrypt_4.4.36.orig.tar.xz
 b75925e5d2c40abab99f8078c40f2a666125067b080466a38eb670730188ca4a 8356 libxcrypt_4.4.36-4build1.debian.tar.xz
Files:
 0d17b69b62b88547bf8d634066656061 392732 libxcrypt_4.4.36.orig.tar.xz
 7de3ee8cfcc3b35181ded060228a26f9 8356 libxcrypt_4.4.36-4build1.debian.tar.xz
Original-Maintainer: Marco d'Itri <md@linux.it>

-----BEGIN PGP SIGNATURE-----

iQJHBAEBCgAxFiEET7WIqEwt3nmnTHeHb6RY3R2wP3EFAmYUFuMTHGp1bGlhbmtA
dWJ1bnR1LmNvbQAKCRBvpFjdHbA/cZvRD/99QuIV9zYXYSv/lC9S/16uQS8vah9e
vKLKtDOmV09mW6WhCA9i/gJp1USpUpgTKeD2TS0a0S8qXhpBNYbvpGca0BjxOqb0
FgbFrn2Q5cX/qZhUqNcYYXCmH38K/+NiEBwCmYzMYde9yyRsLMG0PfrfkwmRGXGw
y3tiCdwCApZQgRzPI8cjyWKD/OIqMU1MlOPKGi09Nf2QBFqq5VxU+ez2kG0deeVV
Mh2BtkU9za9Ch5zutlodsQBgnHUx1nqRBDyNtzIxs+BrB757V+3gA5QHgR/nFfQG
S1pGNp+5lTiTghg8s2mwwPSo28uf5ExeTccV9g+1W0S2PzTN10q6jW+q2UbvUPOf
7k9CZoYGyaU5MMZVE0wotGf4P1l7dLY/2oAqvKeMt9C0UMUgjGnrAqvPD7I/pFrh
RF0NFS7eyFocJxVxAwCUfRuQkGxgArnyw7UnxktxcEG1DKlxTP+IjOv0fiax8Xt7
TuQrUinmxF+zaqpiv5mn/2bg2ehVSLJeGme44mF43nTgyVnvU+w6wxvhWfitSf2g
Oi7w6TfckwNnArMH8M/MMu7UyrRH0gpW1vb1mXaN6h0dXZLY/Qq9hS3rmq4pRFEP
4FDE1Jq0i1ugfSjXhTrnjPgWh09i+bNdY0D3MZnyJlKf1Lrcel7sI6bmL9CAqj8b
eMnzMwqx4pcLsA==
=JWTk
-----END PGP SIGNATURE-----
