-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: libssh
Binary: libssh-4, libssh-gcrypt-4, libssh-dev, libssh-gcrypt-dev, libssh-doc
Architecture: any all
Version: 0.10.6-2ubuntu0.4
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Mike Gabriel <sunweaver@debian.org>, Martin Pitt <mpitt@debian.org>
Homepage: https://www.libssh.org/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/libssh
Vcs-Git: https://salsa.debian.org/debian/libssh.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, libglib2.0-dev, openssh-client
Build-Depends: cmake (>= 2.8.5), debhelper-compat (= 13), libcmocka-dev <!nocheck>, libgcrypt-dev, libkrb5-dev | heimdal-dev, libssl-dev, zlib1g-dev | libz-dev, openssh-client <!nocheck>, openssh-server <!nocheck>, pkg-config, python3:any <!nocheck>
Build-Depends-Indep: doxygen <!nodoc>, graphviz <!nodoc>
Package-List:
 libssh-4 deb libs optional arch=any
 libssh-dev deb libdevel optional arch=any
 libssh-doc deb doc optional arch=all profile=!nodoc
 libssh-gcrypt-4 deb libs optional arch=any
 libssh-gcrypt-dev deb libdevel optional arch=any
Checksums-Sha1:
 e8fb3b4750db11d2483cac4b5f046e301c09b72f 561036 libssh_0.10.6.orig.tar.xz
 ef01c0d5506ae2c6d3fbda6c89dca53079f422d6 833 libssh_0.10.6.orig.tar.xz.asc
 218a62f0a90dc7ee0b9564f709d47d8263bca91e 56400 libssh_0.10.6-2ubuntu0.4.debian.tar.xz
Checksums-Sha256:
 1861d498f5b6f1741b6abc73e608478491edcf9c9d4b6630eef6e74596de9dc1 561036 libssh_0.10.6.orig.tar.xz
 140420406d7796548b0beaf736e73864c32291787cf2bd3983fdbc41741494ae 833 libssh_0.10.6.orig.tar.xz.asc
 13cb7f1a5b294bf5b0a9970acf22a7ccdfca5be546495b930960f0508725e4b9 56400 libssh_0.10.6-2ubuntu0.4.debian.tar.xz
Files:
 5f46371aa8bfa7e6bff7f2a6f3edf80e 561036 libssh_0.10.6.orig.tar.xz
 75a12048601da804564cfa523bd77bcf 833 libssh_0.10.6.orig.tar.xz.asc
 6ae19116fab09b8c350b2ef600bad268 56400 libssh_0.10.6-2ubuntu0.4.debian.tar.xz
Original-Maintainer: Laurent Bigonville <bigon@debian.org>

-----BEGIN PGP SIGNATURE-----

iQHRBAEBCgA7FiEEcxdv4gCCE8W9nrt5a1+PL+d1/EgFAmmxSK8dHGlhbi5jb25z
dGFudGluQGNhbm9uaWNhbC5jb20ACgkQa1+PL+d1/EhuOgwApdybRhNEqyrcwS02
D3kOilTmRl1h043aukM4mgRy0DOUqtmd6bX3GZx+Zuh33/P8ymdTrg8tg6cf85vl
XBomkQGVi7+4fi99qWhDa23BRgkb9F4FveLFlOFnxttsSRY1ooInSm1Z8Zdglbx5
7/n+h6VUL8XsMWhwwMnKFg+CuQQDhaLbueD4LFtsVAeuBdMdaWDsa7dvAmAZFauY
wgWydy3SasndVMhVpzBszD6biHyE20/Aupo33nDrgNO/qtdsIPUTPcyms+MS/84b
XtEd4IbYo5EdZ5SSGMbELmHzh+7YY0Q/q7WDS2v1+Uq+1DE1NnQaXyDLwGg9P6co
Dyjxkhf7M6p0CfE9Q3BG0hIy8wmi3jKhqwHltBQVlSm5lxYSeo680SNXukBfEPkB
75jqoY8KJAWiTVL61J+jBjGaiUFfNF8F4CRCiAgDQU2l+nWQTzX1NwBA8/W+7g5y
/kqJEgbavvehwu5zl+ZfYRARYXROHtWAOD9wTQI0nIyAzTW7
=JfSY
-----END PGP SIGNATURE-----
