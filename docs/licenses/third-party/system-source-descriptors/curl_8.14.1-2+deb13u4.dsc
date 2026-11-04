-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: curl
Binary: curl, libcurl4t64, libcurl3t64-gnutls, libcurl4-openssl-dev, libcurl4-gnutls-dev, libcurl4-doc
Architecture: any all
Version: 8.14.1-2+deb13u4
Maintainer: Debian Curl Maintainers <team+curl@tracker.debian.org>
Uploaders: Carlos Henrique Lima Melara <charlesmelara@riseup.net>, Samuel Henrique <samueloph@debian.org>, Sergio Durigan Junior <sergiodj@debian.org>
Homepage: https://curl.se/
Standards-Version: 4.7.2
Vcs-Browser: https://salsa.debian.org/debian/curl
Vcs-Git: https://salsa.debian.org/debian/curl.git
Testsuite: autopkgtest
Testsuite-Triggers: @builddeps@, build-essential, gcc, libc-dev, libcurl-dev, libldap-dev, pkgconf, slapd
Build-Depends: dpkg-dev (>= 1.22.5), debhelper-compat (= 13), autoconf, automake, ca-certificates, groff-base, libbrotli-dev, libgnutls28-dev, libidn2-dev, libkrb5-dev, libldap2-dev <!pkg.curl.noldap>, libnghttp2-dev, libpsl-dev, librtmp-dev, libssh2-1-dev, libssl-dev, libtool, libzstd-dev, locales-all <!nocheck>, libngtcp2-dev (>= 1.2.0), libngtcp2-crypto-gnutls-dev (>= 1.2.0), libnghttp3-dev (>= 1.1.0), openssh-server <!nocheck>, python3:native <!nocheck>, python3-impacket [!alpha !hppa !m68k !sh4] <!nocheck>, gnutls-bin [!ppc64el] <!nocheck>, quilt, stunnel4 <!nocheck>, zlib1g-dev
Build-Conflicts: autoconf2.13, automake1.4
Package-List:
 curl deb web optional arch=any
 libcurl3t64-gnutls deb libs optional arch=any
 libcurl4-doc deb doc optional arch=all
 libcurl4-gnutls-dev deb libdevel optional arch=any
 libcurl4-openssl-dev deb libdevel optional arch=any
 libcurl4t64 deb libs optional arch=any
Checksums-Sha1:
 d84a4b8baf1baaca33e31e809f5e770deb727c2f 4250332 curl_8.14.1.orig.tar.gz
 c892a3257a40081f754b33e6a10eca2453860307 488 curl_8.14.1.orig.tar.gz.asc
 0ec1460dd39eefc1f1d8eb7f3098ea6dc6a21fff 71840 curl_8.14.1-2+deb13u4.debian.tar.xz
Checksums-Sha256:
 6766ada7101d292b42b8b15681120acd68effa4a9660935853cf6d61f0d984d4 4250332 curl_8.14.1.orig.tar.gz
 39cc2ec8ddc39d04e3e7101bbed46d858d0875cbb297a6bfa20959fa2bc7d5c7 488 curl_8.14.1.orig.tar.gz.asc
 7234af1270610927f24c5c4b74c661451af2b7f28c6207e9133c2b354ee988c5 71840 curl_8.14.1-2+deb13u4.debian.tar.xz
Files:
 745dfc1da8c44eb9ce6ede16fd102c32 4250332 curl_8.14.1.orig.tar.gz
 e90da3c198bfec67be08392e2a974103 488 curl_8.14.1.orig.tar.gz.asc
 77f56fb3436190b379ba0722399f16a7 71840 curl_8.14.1-2+deb13u4.debian.tar.xz

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEBdtqg34QX0sdAsVfu6n6rcz7RwcFAmpAmvgACgkQu6n6rcz7
RwcmrQ//eDZ61QUzjgiJaRqWC0VcPHulh/zYu4Ywl/nyldj1SHLH9kPAEC4ocQ9Z
LcXkWAEkmiqGN2MbTGBOA11nb+HFlg7FKDG1r7vAV3m/9hbU7f5JxRJn7hM5bjvu
6gvZG+Qs+mYK1Gx4Pf50kcMBrGf3PObjEub8jo8weMlRKLBWTqd+uQE5dxYQqy64
FFrm8i71phb+ajrbD/syRqdbTGv4klPDzBQeSV7KKsV3PgPhsFU70uWrbXWzBKAL
GaRNjgANTRweqzRUH75dSi9z/mL1BMwB9I1/niDEQfxRtIxA8yzXfRrE4y4DD5SZ
EzM88AuuA2vW72I8H8nxsQKhfhnfl/fIlsiWKyyNYle9+UTse3IA/LIwajjf3mmt
Qvs3AXqxxs7whPmu7cSIUAqG/eiQjJCf+OAMn1LTOeE7/EsydTY+KT6Pc5+ymbVH
8OhsKX2kb2FsMKYjWsWC3hTcWwliyuvNAyiy5oPMaTHV+/Q2tKweWJT/JIAqXEFS
SFAXnO1udDmeZU3YZ9s02wVLs9omPaGlvqzqLbHIM6b4TyNNofR8jAjR8LSrTfX8
EEO0kJHTqqLPWin3/e7DnzsAVrbjwHURtMMFPqvs9WNiyHA1+bOoP4XNrax5iz1t
/GhhrV0DWe1lalVx9HE7AvfmKIyMDnPfq71Ga//pXaXTp7A4xvo=
=evvY
-----END PGP SIGNATURE-----
