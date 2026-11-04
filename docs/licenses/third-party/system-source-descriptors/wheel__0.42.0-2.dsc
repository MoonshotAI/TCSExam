-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: wheel
Binary: python3-wheel, python-wheel-common, python3-wheel-whl
Architecture: all
Version: 0.42.0-2
Maintainer: Debian Python Team <team+python@tracker.debian.org>
Uploaders: Stefano Rivera <stefanor@debian.org>
Homepage: https://github.com/pypa/wheel
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/python-team/packages/wheel
Vcs-Git: https://salsa.debian.org/python-team/packages/wheel.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, coreutils, python3-all-dev, python3-pytest, python3-pytest-cov, python3-setuptools
Build-Depends: debhelper-compat (= 13), dh-python (>= 6), flit, pybuild-plugin-pyproject, python3-all-dev, python3-pytest <!nocheck>, python3-pytest-cov <!nocheck>, python3-sphinx <!nodoc>, tox (>= 4) <!nocheck>
Package-List:
 python-wheel-common deb python optional arch=all
 python3-wheel deb python optional arch=all
 python3-wheel-whl deb python optional arch=all
Checksums-Sha1:
 cba7e1b72e105ce2163cd1b3c2462a1267b6d8f1 98667 wheel_0.42.0.orig.tar.gz
 797bf14285d64e6a7ff45f09c007c96f73bb2606 7536 wheel_0.42.0-2.debian.tar.xz
Checksums-Sha256:
 c45be39f7882c9d34243236f2d63cbd58039e360f85d0913425fbd7ceea617a8 98667 wheel_0.42.0.orig.tar.gz
 2c37ddf9be2c70886b4b7f15cd454337b6088550f315551856df6025a1e354d5 7536 wheel_0.42.0-2.debian.tar.xz
Files:
 802ad6e5f9336fcb1c76b7593f0cd22d 98667 wheel_0.42.0.orig.tar.gz
 e1463e94c3ec07803e80bdb9d346c26b 7536 wheel_0.42.0-2.debian.tar.xz

-----BEGIN PGP SIGNATURE-----

iIoEARYKADIWIQTumtb5BSD6EfafSCRHew2wJjpU2AUCZecdJxQcc3RlZmFub3JA
ZGViaWFuLm9yZwAKCRBHew2wJjpU2MxAAP9M3NxGK9R7OrywUmhcwtp8bSBweUyI
Z0i1tJdpxBPEZQD+NUmjuquNB23wZGxP7ydXP/LvIQGs4dEFZEkmhcvtJgc=
=d8FG
-----END PGP SIGNATURE-----
