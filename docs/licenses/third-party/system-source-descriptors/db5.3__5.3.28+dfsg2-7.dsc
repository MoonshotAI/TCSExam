-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA384

Format: 3.0 (quilt)
Source: db5.3
Binary: db5.3-doc, libdb5.3-dev, libdb5.3t64, db5.3-util, libdb5.3++t64, libdb5.3++-dev, libdb5.3-dbg
Architecture: any all
Version: 5.3.28+dfsg2-7
Maintainer: Debian QA Group <packages@qa.debian.org>
Homepage: http://www.oracle.com/technetwork/database/database-technologies/berkeleydb/overview/index.html
Standards-Version: 3.9.6
Vcs-Browser: https://salsa.debian.org/debian/db5.3
Vcs-Git: https://salsa.debian.org/debian/db5.3.git
Build-Depends: dpkg-dev (>= 1.22.5), debhelper (>= 10), tcl <cross !pkg.db5.3.notcl>, tcl-dev <!pkg.db5.3.notcl>, procps [!hurd-i386] <!nocheck>
Package-List:
 db5.3-doc deb doc optional arch=all
 db5.3-util deb database optional arch=any
 libdb5.3++-dev deb libdevel optional arch=any
 libdb5.3++t64 deb libs optional arch=any
 libdb5.3-dbg deb debug optional arch=any
 libdb5.3-dev deb libdevel optional arch=any
 libdb5.3t64 deb libs optional arch=any
Checksums-Sha1:
 c2e52e52021c4df2ebff57f1fb68e2879d65376a 21287688 db5.3_5.3.28+dfsg2.orig.tar.xz
 7229d42ffee9d6610e1a09aa397a500bbaee5c12 35232 db5.3_5.3.28+dfsg2-7.debian.tar.xz
Checksums-Sha256:
 ad41b507415dec8316e828b2230242af2251d2c86eefa3c7aa9ef47c5239ef33 21287688 db5.3_5.3.28+dfsg2.orig.tar.xz
 9cee8969e1f440ec8aa2fbacd3a5819907829e0e7e7f1f746dccaa2c93fbf3f2 35232 db5.3_5.3.28+dfsg2-7.debian.tar.xz
Files:
 d98fe4179fb622a9f4abe3afed6a2158 21287688 db5.3_5.3.28+dfsg2.orig.tar.xz
 437d896417d8acac807d1e666850cae8 35232 db5.3_5.3.28+dfsg2-7.debian.tar.xz

-----BEGIN PGP SIGNATURE-----
Version: GnuPG v1.4.14 (MirBSD)

iQIcBAEBCQAGBQJmGoWvAAoJEHa1NLLpkAfgb1cP/ieTdNAciYpywpEGrwYdIJ9z
AwgxzrLwNT65kOgI7vBs1zSnCAHivGZgN2zt/l705PfoBBb39N1m1UAbeiJ1m3wA
KOS3/EXY3Wvatc98q+5h2RzopRUCwyB0mwq/iYjTFOirFiRR2TRYFmpCxShPCv9F
vgLYnHu1HeAUg84DaIlBUMZlJPb96Vf5Y3dT9gzK+jzx1PDSlJmMRSRoBwHcHxM+
ajl/RcBd0Edvz/UQKd3tTP6auKK0vHrHfwVA+oBucyd0/47kvcBliiC72ZJfO9cv
Knvn2CgBpiMiQw1J3DcDIWJaR6DzMVoAPxoaNgUJz34vLuMV3kXbYvInsYOTfs3X
Hoq4qTLud8+zjOSiXHpAeWlNWcPgUwz3gvq38jusDQwOgvOIrPh3+DuDxGfhq8o7
xLfBIbLYaXS8q/BWEBZB0eD+t+4n5p9AzkF/F3lhjIGW1c7Jm9XkEdGA8jkmoRTU
HCsa0EXn58Sb6o43ODAQazA6iL0HLvygRlIEnfrWlwTvh33wS9bYyn7XUhjpgzTB
K4wYeTVRrtSUy2aMSNov8trhZg2Cs3djgOxXmMAzsEcWbNQncM52ZOUx0pJYbNv5
RROlShDwmjCjgg6U40ZSZYVO3zuTO3bn39+fEOPpBzn1L0l1N+EDLp9Mj3EGycAs
xmloOUKyz1tFD4dqlaoS
=o+Du
-----END PGP SIGNATURE-----
