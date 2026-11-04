-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: curl
Binary: curl, libcurl4t64, libcurl3t64-gnutls, libcurl4-openssl-dev, libcurl4-gnutls-dev, libcurl4-doc
Architecture: any all
Version: 8.5.0-2ubuntu10.16
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Carlos Henrique Lima Melara <charlesmelara@riseup.net>, Samuel Henrique <samueloph@debian.org>, Sergio Durigan Junior <sergiodj@debian.org>
Homepage: https://curl.se/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/curl
Vcs-Git: https://salsa.debian.org/debian/curl.git
Testsuite: autopkgtest
Testsuite-Triggers: @builddeps@, gcc, libc-dev, libcurl-dev, libldap-dev, pkgconf, slapd
Build-Depends: dpkg-dev (>= 1.22.5), debhelper-compat (= 13), autoconf, automake, ca-certificates, dh-exec, groff-base, libbrotli-dev, libgnutls28-dev, libidn2-dev, libkrb5-dev, libldap2-dev, libnghttp2-dev, libpsl-dev, librtmp-dev, libssh-dev, libssh2-1-dev, libssl-dev, libtool, libzstd-dev, locales-all <!nocheck>, openssh-server <!nocheck>, python3:native <!nocheck>, python3-impacket [!i386] <!nocheck>, gnutls-bin [amd64 arm64 armel armhf i386 mips64el mipsel s390x powerpc ppc64 riscv64] <!nocheck>, quilt, stunnel4 [!i386] <!nocheck>, zlib1g-dev
Build-Conflicts: autoconf2.13, automake1.4
Package-List:
 curl deb web optional arch=any
 libcurl3t64-gnutls deb libs optional arch=any
 libcurl4-doc deb doc optional arch=all
 libcurl4-gnutls-dev deb libdevel optional arch=any
 libcurl4-openssl-dev deb libdevel optional arch=any
 libcurl4t64 deb libs optional arch=any
Checksums-Sha1:
 d7877b39b6efda66e9ac5f9c28b8b28d8c0b7b7e 4372979 curl_8.5.0.orig.tar.gz
 09c03eb79fb716fe7c6842576ef03ce54c8d086f 97764 curl_8.5.0-2ubuntu10.16.debian.tar.xz
Checksums-Sha256:
 05fc17ff25b793a437a0906e0484b82172a9f4de02be5ed447e0cab8c3475add 4372979 curl_8.5.0.orig.tar.gz
 4ccc6c6a0c4b41c4d753d60c2991541c7f2a41d81c0000f582cf6b4901c746a4 97764 curl_8.5.0-2ubuntu10.16.debian.tar.xz
Files:
 0bc69288b20ae165ff4b7d6d7bbe70d2 4372979 curl_8.5.0.orig.tar.gz
 ded4ebc4a6b0b41fa84e58145c2a8098 97764 curl_8.5.0-2ubuntu10.16.debian.tar.xz
Original-Maintainer: Debian Curl Maintainers <team+curl@tracker.debian.org>

-----BEGIN PGP SIGNATURE-----

iQJSBAEBCgA8FiEEtNElVmlvlJD9Tt9SD2QDvITYlW8FAmrOQ4geHGNoYXJsZXMu
Y29jaHJhbkBjYW5vbmljYWwuY29tAAoJEA9kA7yE2JVvmoMP/Aonbpb/BWPVj0Ru
HQ7UyuZLOEDU2PSHo0wB2172OI1cEi9xHXHi8iz8LKKLcPwg6ozDmXwaw6pMUGgx
Z6UW4wCoH6lhYC0CB4WL0Qk5YhubevSQwzzV/8d8yPfqUPG7sStchh1M+8WBQ8Xt
1vx49DaKs7RscLnb/UUL5+evJyxQjR3cvcmZw+REQE4iJO0peRKVIypDwuGTeA5c
xPzip004g3mIZx0MhSK8aR/OztydLM3VBjRa1Nho3fEi6RLEzH+Lxbdo851xr7/F
2S5jPUF6NU0pwW/j01paVxxRD6nBb15E3tRrzBXIF8iXhAmrCKX4xZTohxISZfKE
IWGG4RnjQQkXo6pyFS5BA3vGrW/0jBqSS+efdnb7qyngqyfvMZ5xI+2/lOlitDGn
c2yh2arMeJaos/JPCIReq81T6g9/PPemXobdiCxEiWQJ6vMDQrRXD982ZpkhPm4N
7F4iDdbQ5qud3rcMIaMhzlzd1srs3TGfWGPiagNd6PHQbFzNVKP4AZ7fsUqw12Sx
4puRED7pwShABP4lzOzsD3suYla1YsIblHZ9fKEjdG48cDHiLduVsQRzRbYWJnpo
+OzKJl8ePilRESrWSh97bh6QkE75a5Eg8OFZ6gXFcXQyFbkqqI1HNVuiXKI0sBxz
F26Gpfdyzn7B77H8b/QWTbbAhHGE
=cpxD
-----END PGP SIGNATURE-----
