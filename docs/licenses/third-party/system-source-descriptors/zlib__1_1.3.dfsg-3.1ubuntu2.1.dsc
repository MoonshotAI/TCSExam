-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: zlib
Binary: zlib1g, zlib1g-dev, zlib1g-udeb, lib64z1, lib64z1-dev, lib32z1, lib32z1-dev, libn32z1, libn32z1-dev, libx32z1, libx32z1-dev, minizip, libminizip1t64, libminizip-dev
Architecture: any
Version: 1:1.3.dfsg-3.1ubuntu2.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Homepage: http://zlib.net/
Standards-Version: 4.6.1
Build-Depends: dpkg-dev (>= 1.22.5), debhelper (>= 13), gcc-multilib [amd64 i386 kfreebsd-amd64 mips mipsel powerpc ppc64 s390 sparc s390x mipsn32 mipsn32el mipsr6 mipsr6el mipsn32r6 mipsn32r6el mips64 mips64el mips64r6 mips64r6el x32] <!nobiarch>, autoconf
Package-List:
 lib32z1 deb libs optional arch=amd64,ppc64,kfreebsd-amd64,s390x profile=!nobiarch
 lib32z1-dev deb libdevel optional arch=amd64,ppc64,kfreebsd-amd64,s390x profile=!nobiarch
 lib64z1 deb libs optional arch=sparc,s390,i386,powerpc,mips,mipsel,mipsn32,mipsn32el,mipsr6,mipsr6el,mipsn32r6,mipsn32r6el,x32 profile=!nobiarch
 lib64z1-dev deb libdevel optional arch=sparc,s390,i386,powerpc,mips,mipsel,mipsn32,mipsn32el,mipsr6,mipsr6el,mipsn32r6,mipsn32r6el,x32 profile=!nobiarch
 libminizip-dev deb libdevel optional arch=any
 libminizip1t64 deb libs optional arch=any
 libn32z1 deb libs optional arch=mips,mipsel profile=!nobiarch
 libn32z1-dev deb libdevel optional arch=mips,mipsel profile=!nobiarch
 libx32z1 deb libs optional arch=amd64,i386
 libx32z1-dev deb libdevel optional arch=amd64,i386
 minizip deb utils optional arch=any
 zlib1g deb libs required arch=any
 zlib1g-dev deb libdevel optional arch=any
 zlib1g-udeb udeb debian-installer optional arch=any
Checksums-Sha1:
 1013da3e3125946039f2c60e291a54a9422b4553 1128572 zlib_1.3.dfsg.orig.tar.xz
 88c2c3108cc0290e020ffc23d8ac60cf5917149f 61028 zlib_1.3.dfsg-3.1ubuntu2.1.debian.tar.xz
Checksums-Sha256:
 5eea0322c1c21c75cad3b607ac1c43ff5c71e014b8ac4a34300b5e2b80d02e70 1128572 zlib_1.3.dfsg.orig.tar.xz
 958c7031c02f894516492954153c8d760d94e20a4039e48ca7231880b913ae26 61028 zlib_1.3.dfsg-3.1ubuntu2.1.debian.tar.xz
Files:
 3eee75fc36a344cfe93c8bf1c0473df4 1128572 zlib_1.3.dfsg.orig.tar.xz
 9e68275943ece8de88954558020c5d41 61028 zlib_1.3.dfsg-3.1ubuntu2.1.debian.tar.xz
Original-Maintainer: Mark Brown <broonie@debian.org>
-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEVovyKmYzfL/Jprm3LIPbyOm9DjcFAma1gjQACgkQLIPbyOm9
DjdA8A//XD6pq/mAkEkmQm1a83d/QrQGU6IqUWilPY4WqwumobWzHE8BZ6uyk2Z1
RPBZ4ObX075CtrMNjGDUlyzVlHZn6naKlvm7LAyEXnC/81flA5derkirIIQz8lBJ
CcBjGLHy73AxeebdJA/Tm/OmiAC2gUYfjdTA0JyV5cxqigwP0OvBQg9LeZr1TtFr
dh3R+1/9mQ/n7WCCMlG0qo+ttITOsBVxFxLWOfTVoV1AShy+jRjvfAJSqW88+iV2
Equ3VcMKb1xkyO4Zr8tATjvbtsEz70wLca4iMSsmtrSjahKkCtHZVjyUQ6vS+Ljt
lMarQdZpp1C4hDEVBQ7vA+1ykmuGiEmFrN1eqWb5ZmzxiaqTweBgqf/R8ikcuCOy
HeO04A+tn/DjTG0HJ/DCUiiiOVQ2cI5ReeCcCpzAPJqYUO6xjiXJ2oExM3K5u95k
zr4hShp2dh29bMm3O20lM5QvxgmGBq/xEyTqSVm55sxr3EfWy2yyo0/k/+kyXpHw
UIKOEaYd7MxH8LRRtTrJPzKy8/NNjmUTQnqgh8BMMom8G5enVLS//guB8CqJ48gy
EuWoH7gjZymIC7zNyjN+3TujV5hMdCL0ieVW5cGxRrTc8VIUKCYxkr7TUOlmf0JF
u0REZFo41ItnIED1OU37U8hZoWv/qGg/M9EXlyIW86aVDDOlITc=
=NUrw
-----END PGP SIGNATURE-----
