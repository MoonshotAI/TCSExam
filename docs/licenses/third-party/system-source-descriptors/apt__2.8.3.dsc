-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (native)
Source: apt
Binary: apt, libapt-pkg6.0t64, apt-doc, libapt-pkg-dev, libapt-pkg-doc, apt-utils, apt-transport-https
Architecture: any all
Version: 2.8.3
Maintainer: APT Development Team <deity@lists.debian.org>
Uploaders: Michael Vogt <mvo@debian.org>, Julian Andres Klode <jak@debian.org>, David Kalnischkies <donkult@debian.org>
Standards-Version: 4.1.1
Vcs-Browser: https://salsa.debian.org/apt-team/apt
Vcs-Git: https://salsa.debian.org/apt-team/apt.git
Testsuite: autopkgtest
Testsuite-Triggers: @builddeps@, aptitude, db-util, dpkg, fakeroot, g++, gdb, gdb-minimal, gnupg, gnupg1, gnupg2, gpgv, gpgv1, gpgv2, libfile-fcntllock-perl, lsof, pkg-config, python3-apt, stunnel4, valgrind, wget
Build-Depends: dpkg-dev (>= 1.22.5) <!pkg.apt.ci>, cmake (>= 3.4), debhelper-compat (= 12), docbook-xml <!nodoc>, docbook-xsl <!nodoc>, dpkg-dev (>= 1.20.8), gettext (>= 0.12), googletest <!nocheck> | libgtest-dev <!nocheck>, libbz2-dev, libdb-dev, libgnutls28-dev (>= 3.4.6), libgcrypt20-dev, liblz4-dev (>= 0.0~r126), liblzma-dev, libseccomp-dev (>= 2.4.2) [amd64 arm64 armel armhf i386 mips mips64el mipsel ppc64el s390x hppa powerpc powerpcspe ppc64 x32], libsystemd-dev [linux-any], libudev-dev [linux-any], libxxhash-dev (>= 0.8), libzstd-dev (>= 1.0), ninja-build, pkg-config, po4a (>= 0.34-2) <!nodoc>, triehash, xsltproc <!nodoc>, zlib1g-dev
Build-Depends-Indep: doxygen <!nodoc !pkg.apt.nodoxygen>, graphviz <!nodoc !pkg.apt.nodoxygen>, w3m <!nodoc>
Package-List:
 apt deb admin required arch=any
 apt-doc deb doc optional arch=all profile=!nodoc
 apt-transport-https deb oldlibs optional arch=all
 apt-utils deb admin required arch=any
 libapt-pkg-dev deb libdevel optional arch=any
 libapt-pkg-doc deb doc optional arch=all profile=!nodoc
 libapt-pkg6.0t64 deb libs optional arch=any
Checksums-Sha1:
 3dff624f3ddac2ff2d5b926cdfff8fe4dfbb8d96 2354680 apt_2.8.3.tar.xz
Checksums-Sha256:
 088522b3613b28fdbcfa61f1f7e476bf6dc6b0120a8f74409e9527580c9f9d3b 2354680 apt_2.8.3.tar.xz
Files:
 eb9c22f076b23b33421715d38751260c 2354680 apt_2.8.3.tar.xz

-----BEGIN PGP SIGNATURE-----

iQJDBAEBCgAtFiEET7WIqEwt3nmnTHeHb6RY3R2wP3EFAmcZD4IPHGpha0BkZWJp
YW4ub3JnAAoJEG+kWN0dsD9xkpgP/ixRBDv7iFhyRIai6r952fCEwgVTP4w+Fftg
1EnXaYv7l0hl/kYVrdilIIBh6HzH3PeDK3KGBKQJSCaPn/lzshexhgLJqmrhqa6w
fdcJwixrLDgR9HW/oIcuki+hfyfQgnz6hbwYRoW0RoR9KGdbnCVN6//GN0Zrp99J
BFLad8a4VzQ+/wbqtM4AxBfAfnK31P4669FCIvm+mrXhTsQZ6i6L0zz4X4du1F8f
fqJ/PKLIZK0KaZFBILqpxNY2CGB5c4SdqnjKbqcfS/OW/5q1htGnZfChVMe5oji9
dj4cyZQJHipIV0o2oYeg0KlzBx8PW4/bcpP2IzLHNaMYdecEV6oMdf1yMCESbx29
fTEkq9o9x4o4EU8gIjUdzHAqWoDwQI3pd4JVYasvBEkk8UuzTGnte37NoncZKXg2
DY1XgmEdP9mFCFZ9AcpttTVYFcDiB7fySMfi7zI6+2uDllh4gll9N83+Qbu5Wh+e
lo8+WGmPlk7eYbvJAWuL3X9a+QEee6VMUMdzvpRFJ+O7hsjnEHixbziy5KMEZlzy
vBxgRN5Mw+4fdG6MaO7/zW1I8TtXBiAFZc4PEhGHwvRp77gZe5CIOu8WOt63YYKV
6078RTDHQgWgJSZfbYe75qXH1a3Qjj1jhcsRUuVHFWD/gi5CR9tRT4Jii8YcMQSH
WPoJRsUA
=QC7p
-----END PGP SIGNATURE-----
