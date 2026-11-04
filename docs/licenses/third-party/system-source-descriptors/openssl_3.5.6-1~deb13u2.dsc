-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: openssl
Binary: openssl, openssl-provider-legacy, openssl-provider-fips, libssl3t64, libcrypto3-udeb, libssl3-udeb, libssl-dev, libssl-doc
Architecture: any all
Version: 3.5.6-1~deb13u2
Maintainer: Debian OpenSSL Team <pkg-openssl-devel@alioth-lists.debian.net>
Uploaders: Christoph Martin <christoph.martin@uni-mainz.de>, Kurt Roeckx <kurt@roeckx.be>, Sebastian Andrzej Siewior <sebastian@breakpoint.cc>
Homepage: https://openssl-library.org
Standards-Version: 4.7.2
Vcs-Browser: https://salsa.debian.org/debian/openssl
Vcs-Git: https://salsa.debian.org/debian/openssl.git
Testsuite: autopkgtest
Testsuite-Triggers: perl
Build-Depends: debhelper-compat (= 13), dpkg-dev (>= 1.22.5), libzstd-dev, zlib1g-dev
Package-List:
 libcrypto3-udeb udeb debian-installer optional arch=any profile=!noudeb profile:v1=!noudeb
 libssl-dev deb libdevel optional arch=any
 libssl-doc deb doc optional arch=all
 libssl3-udeb udeb debian-installer optional arch=any profile=!noudeb profile:v1=!noudeb
 libssl3t64 deb libs optional arch=any
 openssl deb utils optional arch=any
 openssl-provider-fips deb utils optional arch=any
 openssl-provider-legacy deb utils optional arch=any
Checksums-Sha1:
 3dc26853ca7683237a869d01745dae48fb63ed82 53121812 openssl_3.5.6.orig.tar.gz
 9e66b9879c7b021d9b169e2078909256cf9f3f49 833 openssl_3.5.6.orig.tar.gz.asc
 6146ebc0d50f32fdaa59185ade423c50a186d7d0 82144 openssl_3.5.6-1~deb13u2.debian.tar.xz
Checksums-Sha256:
 deae7c80cba99c4b4f940ecadb3c3338b13cb77418409238e57d7f31f2a3b736 53121812 openssl_3.5.6.orig.tar.gz
 581c536bd4c5bf7e325feaa90d6ce01c3da297737b5be3213c4e8087323fb623 833 openssl_3.5.6.orig.tar.gz.asc
 322797f9ac320606e91eb07540fd4c7ba910ee84f52fa455c7f8619dd53f9bcc 82144 openssl_3.5.6-1~deb13u2.debian.tar.xz
Files:
 1bb3506c580865a0a464e09288ac157e 53121812 openssl_3.5.6.orig.tar.gz
 0a28e7f4a64dcd78e13a850c98cd1a32 833 openssl_3.5.6.orig.tar.gz.asc
 1d79eaa496b080cf95c004589beb2583 82144 openssl_3.5.6-1~deb13u2.debian.tar.xz

-----BEGIN PGP SIGNATURE-----

iQGzBAEBCgAdFiEEV4kucFIzBRM39v3RBWQfF1cS+lsFAmokjBwACgkQBWQfF1cS
+lvCOwwAgjvIQkb+K5zLnd2w1oDWW6P54NtDHU0Y46fUjoJ/Tnz/gQ5W406Und9b
UwfeerpSZyfhSXztu8kXzrnkSGNe7GbWyXf4SHQJFMqGFYCjri699hYArCT+a/pw
qqKxOAUBZj8sZL0vwi2gZRl7N80/vrHQkbCRnBol25AJ2a4pa9+AvDy/S4Q/UtUD
QyEodMiqOAjBhtZHBHJpxZ55Ulg2CwtGAJYhAfh+oGMN0bwgb0ThTiX803z9uYK5
0Vthu70eOgzrx4vrlrSeEHrx+7fYuX3d92jlTKSKqjQhmX8QZIs8lKpgXp7Wp55N
dnogRWTRgWzke+EmZG6cCVWAiVqVRrhqkTCaVxqaz7BC5A805Dv3hdUnfr71ZKgQ
8HTbflMTtIK3KIpqj7OG1SflG8SjUsMV22vRiDEIHXZq9zoXi9FJCCpdYx1stEgw
TvmGgjg8NNdURF43R6f4c5IwVMJdx0uiChG2w5dhTZSiEqFqKOGaC0GTmwEnfizh
Yi9QrFLd
=4gOc
-----END PGP SIGNATURE-----
