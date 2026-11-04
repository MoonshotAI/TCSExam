-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: xz-utils
Binary: liblzma5, liblzma5-udeb, xz-utils, xzdec, liblzma-dev, liblzma-doc
Architecture: any all
Version: 5.8.1-1+deb13u2
Maintainer: Sebastian Andrzej Siewior <sebastian@breakpoint.cc>
Uploaders: Jonathan Nieder <jrnieder@gmail.com>
Homepage: https://tukaani.org/xz/
Standards-Version: 4.7.2
Vcs-Browser: https://salsa.debian.org/debian/xz-utils
Vcs-Git: https://salsa.debian.org/debian/xz-utils.git
Testsuite: autopkgtest
Testsuite-Triggers: autoconf, automake, debhelper-compat, gettext, libtool
Build-Depends: debhelper-compat (= 13), dpkg-dev (>= 1.16.2), autoconf (>= 2.64~), automake, libtool (>= 2.2), gettext, autopoint | gettext (<< 0.18-1), autopoint | cvs, po4a
Build-Depends-Indep: doxygen, graphviz
Build-Conflicts: automake1.4
Package-List:
 liblzma-dev deb libdevel optional arch=any
 liblzma-doc deb doc optional arch=all
 liblzma5 deb libs optional arch=any
 liblzma5-udeb udeb debian-installer optional arch=any
 xz-utils deb utils standard arch=any
 xzdec deb utils optional arch=any
Checksums-Sha1:
 c29df8058b6279bfab2744f3e79b2940229207a3 1461872 xz-utils_5.8.1.orig.tar.xz
 3658f92b0eec052a58ca69fa3c12c5b095a05fc6 833 xz-utils_5.8.1.orig.tar.xz.asc
 4d9c41375f1fcc5f8ee0f803e8853257e576da7b 28044 xz-utils_5.8.1-1+deb13u2.debian.tar.xz
Checksums-Sha256:
 0b54f79df85912504de0b14aec7971e3f964491af1812d83447005807513cd9e 1461872 xz-utils_5.8.1.orig.tar.xz
 4138f4ceca1aa7fd2085fb15a23f6d495d27bca6d3c49c429a8520ea622c27ae 833 xz-utils_5.8.1.orig.tar.xz.asc
 7dfcff43a8035561c4860a4893f7cf9de5e977e79a90aee4d101053e21912cb0 28044 xz-utils_5.8.1-1+deb13u2.debian.tar.xz
Files:
 cf5e1feb023d22c6bdaa30e84ef3abe3 1461872 xz-utils_5.8.1.orig.tar.xz
 7a1c93af83d35ba1e0ba9cbe12f01493 833 xz-utils_5.8.1.orig.tar.xz.asc
 157e50dca66f8ce8990bf2b5bb15bc52 28044 xz-utils_5.8.1-1+deb13u2.debian.tar.xz

-----BEGIN PGP SIGNATURE-----

iQGzBAEBCgAdFiEEV4kucFIzBRM39v3RBWQfF1cS+lsFAmq5HswACgkQBWQfF1cS
+lsOlQwAul6X5g4qpHCcOwmRYXIdTOUAc07qfxwy24ePUoU8JQP6uPn40EhK/cDd
6OZxJMlsFSbmitpeSjmJzL10xh1n/HNM3mNyHR6h+Zum6v5ef5KtaXUWO4RxYBLu
bVckrJMm2BI3XSpOCDZ+dgGu4pfYqgoB8W07wzhId+Z5HuIUBvVeow4McEr6Xxj/
SWwUkDEl12DYna19vHJJGBONY2v0j7IKDeqWzWjGoiNoC4w431YUF4YBmj6eVvvX
g072XWys37J5SNTGjv5kY0VjTfLY/b+67aDstZObv1F1MUcMVRWossuHr4o1OFpx
hZ8KUevS4KknU1FEeQgNKocaCP3+JfLpR9+sIlwKtYpUY53GsC0H7IS1aMKKI8LG
NWKt2jT4A+A1AAKooiaETsdc8d+KVhe3TnK/u7Lg1D5EH6pd64c0UekJRk7h18Hb
iDWFsw9DKa68jWjMkugJjDplz7Qw81S9bVAXklWXSBl9HufC9V2ccDCbGxNM9Evz
y1lRiF17
=YLJK
-----END PGP SIGNATURE-----
