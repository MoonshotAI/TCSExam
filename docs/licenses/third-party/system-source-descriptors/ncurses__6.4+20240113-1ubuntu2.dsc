-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: ncurses
Binary: ncurses-base, ncurses-term, libtinfo6, libtinfo6-udeb, libncurses6, libncurses-dev, libncursesw6, libncursesw6-udeb, lib64tinfo6, lib64ncurses6, lib64ncursesw6, lib64ncurses-dev, lib32tinfo6, lib32ncurses6, lib32ncursesw6, lib32ncurses-dev, ncurses-bin, ncurses-examples, ncurses-doc
Architecture: any all
Version: 6.4+20240113-1ubuntu2
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Sven Joachim <svenjoac@gmx.de>, Craig Small <csmall@debian.org>
Homepage: https://invisible-island.net/ncurses/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/ncurses
Vcs-Git: https://salsa.debian.org/debian/ncurses.git
Testsuite: autopkgtest
Build-Depends: debhelper-compat (= 13), libgpm-dev [linux-any], pkgconf, autoconf-dickey (>= 2.52+20210509)
Build-Depends-Arch: g++-multilib [amd64 i386 powerpc ppc64 s390 sparc] <!nobiarch>
Package-List:
 lib32ncurses-dev deb libdevel optional arch=amd64,ppc64 profile=!nobiarch
 lib32ncurses6 deb libs optional arch=amd64,ppc64 profile=!nobiarch
 lib32ncursesw6 deb libs optional arch=amd64,ppc64 profile=!nobiarch
 lib32tinfo6 deb libs optional arch=amd64,ppc64 profile=!nobiarch
 lib64ncurses-dev deb libdevel optional arch=i386,powerpc,sparc,s390 profile=!nobiarch
 lib64ncurses6 deb libs optional arch=i386,powerpc,sparc,s390 profile=!nobiarch
 lib64ncursesw6 deb libs optional arch=i386,powerpc,sparc,s390 profile=!nobiarch
 lib64tinfo6 deb libs optional arch=i386,powerpc,sparc,s390 profile=!nobiarch
 libncurses-dev deb libdevel optional arch=any
 libncurses6 deb libs optional arch=any
 libncursesw6 deb libs optional arch=any
 libncursesw6-udeb udeb debian-installer optional arch=any profile=!noudeb
 libtinfo6 deb libs optional arch=any
 libtinfo6-udeb udeb debian-installer optional arch=any profile=!noudeb
 ncurses-base deb misc required arch=all essential=yes
 ncurses-bin deb utils required arch=any essential=yes
 ncurses-doc deb doc optional arch=all
 ncurses-examples deb misc optional arch=any profile=!pkg.ncurses.noexamples
 ncurses-term deb misc standard arch=all
Checksums-Sha1:
 f68717e15ac773b6bf2370c22d2dca6f7344d333 3688489 ncurses_6.4+20240113.orig.tar.gz
 10de8ab4e14ab72531cd34736fce77b59efe688a 729 ncurses_6.4+20240113.orig.tar.gz.asc
 0efa1687c833bb4619b2ab2fd22116bc47822dd9 49372 ncurses_6.4+20240113-1ubuntu2.debian.tar.xz
Checksums-Sha256:
 37a12a0f8ae2605012c9a164dd286b0cfa02b51b5055836d09eb3d597fc351b1 3688489 ncurses_6.4+20240113.orig.tar.gz
 b70cfa4f155f61dfa7c085ad1e3f90c73132ad198764d7793a44cd7fdca51f1b 729 ncurses_6.4+20240113.orig.tar.gz.asc
 cd2840e65cc833541573616ffe36eae5161c309e62eb6c97c83f08d47e1ebf59 49372 ncurses_6.4+20240113-1ubuntu2.debian.tar.xz
Files:
 e4413199eea72d2cd4e252e9bf9e88b6 3688489 ncurses_6.4+20240113.orig.tar.gz
 19ebd3dca63568f3419507fb505c763c 729 ncurses_6.4+20240113.orig.tar.gz.asc
 829cd32dad384999fcf752b1e5bec376 49372 ncurses_6.4+20240113-1ubuntu2.debian.tar.xz
Original-Maintainer: Ncurses Maintainers <ncurses@packages.debian.org>

-----BEGIN PGP SIGNATURE-----

iQJHBAEBCgAxFiEET7WIqEwt3nmnTHeHb6RY3R2wP3EFAmYUGAITHGp1bGlhbmtA
dWJ1bnR1LmNvbQAKCRBvpFjdHbA/cbCiEACYkmASNkcoI7g5weGCOLguBYk74+E3
qhhHW17MZZeaRRiFjzGKgU1h+/18TXp2Mu9gNBlaT81+VkzsltlOMAvN1geiTiyo
bMoNe1CLSDTPJmmn6bGKNOJ+aS9Qtc1sVt+sTTdX1KSxGOZkvI+HDSf2j9Ps97hO
7CGOkjyyx5h+WvnuvcATkTJE8pujpK0dzlCjzeDvfSA+nM8tvzKH6ovpiQcW4h06
aMZ+zhuIrpgdnCUZkHs8U9ZtXzgK0DCaREoq08WzuO78HaejDwRYmv0FQUj5x52m
oaYfGgspWiwgU8+1SVWX8dJyJw2GbDNP2ZPkvzMui4AvT2Hlb00Qpiibc9bTpz7r
TQq9aLPmBDN1XwSXweaHoxGo88k1JNPw9r1Lx0zybQ0QMjnsBCt2YozoPZrtWRLA
QcvY1PP4Ht81g/2or1cBjJLaDIM85iZkKKgguI0t5Dk9wcE10+6AL/b863uncW5Z
Uo29NtB/22vcdkxIJV6DxhuXWV8NB7OFtmZ3rzp6yfV3di8ky35aZn7zvdBkI/BE
/Xoa1FzvnM9cLVg6YauSi5E+68k7zUhAc0g15U65I4pN3yJzZL156j1z8Q6CG3Ay
Mv1NCXbAhi47REW6r5W/SxbsrkOvcxn+9fqaX12TSJEURjI4hMvBlHNtr7fobQFk
kJNJIUtLc05pYQ==
=O/mn
-----END PGP SIGNATURE-----
