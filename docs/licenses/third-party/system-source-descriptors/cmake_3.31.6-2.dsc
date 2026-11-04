-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: cmake
Binary: cmake, cmake-curses-gui, cmake-data, cmake-doc, cmake-qt-gui
Architecture: any all
Version: 3.31.6-2
Maintainer: Debian CMake Team <pkg-cmake-team@lists.alioth.debian.org>
Uploaders: Lisandro Damián Nicanor Pérez Meyer <lisandro@debian.org>, Felix Geyer <fgeyer@debian.org>, Timo Röhling <roehling@debian.org>,
Homepage: https://cmake.org/
Description: cross-platform, open-source make system
 CMake is used to control the software compilation process using
 simple platform and compiler independent configuration files. CMake
 generates native makefiles and workspaces that can be used in the
 compiler environment of your choice. CMake is quite sophisticated: it
 is possible to support complex environments requiring system
 configuration, pre-processor generation, code generation, and template
 instantiation.
Standards-Version: 4.7.1
Vcs-Browser: https://salsa.debian.org/cmake-team/cmake
Vcs-Git: https://salsa.debian.org/cmake-team/cmake.git
Testsuite: autopkgtest
Testsuite-Triggers: @builddeps@, bison, cvs, default-jdk, doxygen, flex, gettext, git, hspell, icoutils, imagemagick, libarchive-dev, libarmadillo-dev, libasound2-dev, libboost-dev, libbz2-dev, libcups2-dev, libcurl4-openssl-dev, libexpat1-dev, libfreetype6-dev, libgif-dev, libgnutls28-dev, libgtk2.0-dev, liblzma-dev, libmagick++-dev, libmagickcore-dev, libmagickwand-dev, libopenscenegraph-dev, libphysfs-dev, libprotobuf-dev, libtiff5-dev, libxml2-dev, libxslt1-dev, mercurial, ninja-build, perl, pkg-config, protobuf-compiler, python3-dev, ruby-dev, subversion, swig, zlib1g-dev
Build-Depends: debhelper-compat (= 13), cmake <cross>, git <!nocheck>, libarchive-dev (>= 3.3.3) <!pkg.cmake.bootstrap>, libcppdap-dev <!pkg.cmake.bootstrap>, libcurl4-openssl-dev <!pkg.cmake.bootstrap>, libexpat1-dev <!pkg.cmake.bootstrap>, libjsoncpp-dev <!pkg.cmake.bootstrap>, libncurses-dev <!pkg.cmake.bootstrap !pkg.cmake.nogui>, librhash-dev <!pkg.cmake.bootstrap>, libssl-dev <pkg.cmake.bootstrap>, libuv1-dev (>= 1.10) <!pkg.cmake.bootstrap>, procps [!hurd-any], python3-sphinx:native, python3-sphinxcontrib.qthelp:native, qt6-base-dev <!pkg.cmake.bootstrap !pkg.cmake.nogui>, zlib1g-dev <!pkg.cmake.bootstrap>
Build-Depends-Indep: dh-sequence-sphinxdoc
Package-List:
 cmake deb devel optional arch=any
 cmake-curses-gui deb devel optional arch=any profile=!pkg.cmake.bootstrap,!pkg.cmake.nogui
 cmake-data deb devel optional arch=all
 cmake-doc deb doc optional arch=all profile=!pkg.cmake.bootstrap
 cmake-qt-gui deb devel optional arch=any profile=!pkg.cmake.bootstrap,!pkg.cmake.nogui
Checksums-Sha1:
 bc5d7e6c095c25c2de382d0290655cba0af40a9f 11710589 cmake_3.31.6.orig.tar.gz
 34f88af5890c65a0106f065b8c714f943450fae6 34404 cmake_3.31.6-2.debian.tar.xz
Checksums-Sha256:
 653427f0f5014750aafff22727fb2aa60c6c732ca91808cfb78ce22ddd9e55f0 11710589 cmake_3.31.6.orig.tar.gz
 ec672b42c986ca2190453fd78dd0a2adf3004d15f8a2b7eb0124345b178963d1 34404 cmake_3.31.6-2.debian.tar.xz
Files:
 a9f42404b21654a29553a61078accd20 11710589 cmake_3.31.6.orig.tar.gz
 090ca2d9423af57c14a2ef92450ef193 34404 cmake_3.31.6-2.debian.tar.xz
Dgit: d66d7db06e190da9c4cebff7bc6db8348089460a debian archive/debian/3.31.6-2 https://git.dgit.debian.org/cmake

-----BEGIN PGP SIGNATURE-----

iQJIBAEBCgAyFiEEmwPruYMA35fCsSO/zIxr3RQD9MoFAmfqps0UHHJvZWhsaW5n
QGRlYmlhbi5vcmcACgkQzIxr3RQD9MrLrg//REU61skfZaXVuO5VWq3+Fn/BFSfS
ZhETwVEcxQ/w2ggLZOK5wSJKnjnKpDlqWsAZUWBuzuJSyVmNsRXdvrxlZhJYh4Yu
8f393yv/AJgvgdiRLXQohBLgxvnMpBJVpKcViR8+mEL+isJDI6MvRPvT7ET9U6qt
zhve7JlbJvpu8+5hOauiu9KmTm3H2BYu5Sa5qWN8mDa4GafZ/0ETPe6NdUumq+qb
LDLL3i0RxhvXql4qplYhn7z3x6gINKSNh8fIECMJnT/+4+fgn+aVKJ7ng+FARPLP
7yraNm0oGpWqdRhFITj/FLyAx6Z1e5vhTs1+YusmW+MZAb30SIEObZEgcd4S2HPZ
I/mdon47eNYXuUTWm9ftpBppTlWnyjzIhOljfOMoJHzaspiOd40+ABZN78Rb7uup
SPsE8Dm36F4YFiAoOpsrU5Zf/e3UmvT8B1Tq0/v81zOWeeeCPyBe1s9JCqmiPTml
2/G74w0D+y5KVeiB9olla2VO/o/7xg66blEZHGYDcYwBkObHfAJ0xvLUHBUavdiG
0hSJHwmf/yH7Ce5Y4sPkbmK2T/UVGZNowHLtLim1pgpZ6BYsTOW2Wu0Izk1hzFxx
C8pd8PWke33w7DOmUXXcJ4NA9CmZFaD+7umbyUC6Eqmsksm6AlNlP2PehKp1mEHX
FPyuhvRyYeHg+8s=
=IN96
-----END PGP SIGNATURE-----
