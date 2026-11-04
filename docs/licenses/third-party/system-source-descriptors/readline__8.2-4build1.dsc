-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: readline
Binary: libreadline8t64, libreadline8-udeb, lib64readline8, readline-common, readline-common-udeb, libreadline-dev, lib64readline-dev, rlfe, lib32readline8, lib32readline-dev, readline-doc
Architecture: any all
Version: 8.2-4build1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Homepage: https://tiswww.case.edu/php/chet/readline/rltop.html
Standards-Version: 4.6.2
Build-Depends: dpkg-dev (>= 1.22.5), debhelper (>= 13), libncurses-dev, lib32ncurses-dev [amd64 ppc64] <!nobiarch>, lib64ncurses-dev [i386 powerpc sparc s390] <!nobiarch>, mawk | awk, texinfo, gcc-multilib [amd64 i386 kfreebsd-amd64 powerpc ppc64 s390 sparc] <!nobiarch>
Package-List:
 lib32readline-dev deb libdevel optional arch=amd64,ppc64 profile=!nobiarch
 lib32readline8 deb libs optional arch=amd64,ppc64 profile=!nobiarch
 lib64readline-dev deb libdevel optional arch=i386,powerpc,s390,sparc profile=!nobiarch
 lib64readline8 deb libs optional arch=i386,powerpc,s390,sparc profile=!nobiarch
 libreadline-dev deb libdevel optional arch=any
 libreadline8-udeb udeb debian-installer optional arch=any profile=!noudeb
 libreadline8t64 deb libs optional arch=any
 readline-common deb utils optional arch=all
 readline-common-udeb udeb debian-installer optional arch=all profile=!noudeb
 readline-doc deb doc optional arch=all
 rlfe deb utils optional arch=any profile=!cross
Checksums-Sha1:
 97ad98be243a857b639c0f3da2fe7d81c6d1d36e 3043952 readline_8.2.orig.tar.gz
 fe7f860b9404ea038b449a716001074a6ff82245 33816 readline_8.2-4build1.debian.tar.xz
Checksums-Sha256:
 3feb7171f16a84ee82ca18a36d7b9be109a52c04f492a053331d7d1095007c35 3043952 readline_8.2.orig.tar.gz
 d3b4bfa92d0026f5d3f5d2b21e2bf6d8ae163f9ccdebdcef20afde77901c7b70 33816 readline_8.2-4build1.debian.tar.xz
Files:
 4aa1b31be779e6b84f9a96cb66bc50f6 3043952 readline_8.2.orig.tar.gz
 451c114a84e100f903e6f419fb02b6a2 33816 readline_8.2-4build1.debian.tar.xz
Original-Maintainer: Matthias Klose <doko@debian.org>

-----BEGIN PGP SIGNATURE-----

iQJOBAEBCgA4FiEErEg/aN5yj0PyIC/KVo0w8yGyEz0FAmYJHP8aHHN0ZXZlLmxh
bmdhc2VrQHVidW50dS5jb20ACgkQVo0w8yGyEz1rRQ/+JWbu0x/Ao5clPMo+xjwP
NRwyGZYfBVKgMvfhr6Rl1a0upnCl+OkjXIHynhjhWbAAm3qkqFiLGsW/SBWaUZUz
8gfqS2yOE8EKUOJe4RKoT+3Pt9DbB60oakNk2I5Kfd4waxSstT1l8tM+HKQTTA2j
1GknAB9a4+XN24PDJrbR3e4Mr8heGn58JIZulxWhf/ZZOUf9n0n0M0ZNZ+3ZL3BD
mbPWsU61D2Cp81gW+PWKgtBsQFKMIk68G9K3FwAFtUKoONDQDJWCxW70Brw4m3nk
nZIjp2sHsideYwG3f+segzQiTg138wCoxVblV5N6SG6UPrIaLp/xA/7Ttx3PlUx6
LTSiC37K7/czhASSy4kLLCjtlASpgENBUTcLqEgvITcYO8XoxvuMzLDUs8BErF5l
QdkNDwqsa8k4IgxG1eRhz7ZQU41Y5iBFuWeqDm4sDtftGRElAnlq5vl5qhQx3Bnh
D/h9AND5ArLDzPxXrHBB4Oz+RnybKoJeAC3R7K4ShADbTAvun8OL16FiSMpXCFTU
SjvPEOGKJY2G9TqdWsneQ5pFtGVsE/M82vhW7g8IavCMvLsjsRZnKPmUQZzN8kHI
SXGTB90UXczRFmkbcMpKgAo92s100TYc9/A7ZP01BdwMooZCxNyl0jTk88jCjokR
zsxzZLzYsLSrP+ALf8mE1Q4=
=Yl6P
-----END PGP SIGNATURE-----
