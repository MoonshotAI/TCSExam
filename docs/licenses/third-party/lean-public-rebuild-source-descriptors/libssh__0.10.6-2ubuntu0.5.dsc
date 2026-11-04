-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: libssh
Binary: libssh-4, libssh-gcrypt-4, libssh-dev, libssh-gcrypt-dev, libssh-doc
Architecture: any all
Version: 0.10.6-2ubuntu0.5
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
 cc3d0db315a6b703d539a12e7280ceaf20463d09 63744 libssh_0.10.6-2ubuntu0.5.debian.tar.xz
Checksums-Sha256:
 1861d498f5b6f1741b6abc73e608478491edcf9c9d4b6630eef6e74596de9dc1 561036 libssh_0.10.6.orig.tar.xz
 140420406d7796548b0beaf736e73864c32291787cf2bd3983fdbc41741494ae 833 libssh_0.10.6.orig.tar.xz.asc
 5ea1b360802689a7daa557470a661665d95996ab8c0b8dc700083ed8caf8f8d8 63744 libssh_0.10.6-2ubuntu0.5.debian.tar.xz
Files:
 5f46371aa8bfa7e6bff7f2a6f3edf80e 561036 libssh_0.10.6.orig.tar.xz
 75a12048601da804564cfa523bd77bcf 833 libssh_0.10.6.orig.tar.xz.asc
 787df373d6c632c0ca97b56b1b70f913 63744 libssh_0.10.6-2ubuntu0.5.debian.tar.xz
Original-Maintainer: Laurent Bigonville <bigon@debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmqMYh0ACgkQZWnYVadE
vpMt/xAAh7ccREV/ornWOHOoSLInQvGxhe0JrseK84S3HBSQVIkWcbSa3A7X+oDx
MHVep1TVunmnNnoDg7NQxkq+wF5N1bEOLWg8pRkRVseG6EPYfbgV0+sQy+1CpQAc
Ye5NeQKF22E/NwjjG1FJa6kgMinO29FCoJk46mNvEWo1YhvqepJMASXEg5C+7Rxr
wVdXekn0HCid8fPu5BUkBqfwIhJDSEIlLXpFwnpC1wjrzDe/AaBBDV5vnRXdp+P8
NJ4ZvsNP5zg/PwACWl98LpaKhNXJD1vOYOdZ27je4WsOQj15iA2ffoP1odfoTyc+
V7ym1YJkuT38e+9cV3sClmvhYfR4tu/BwJqqYnUzsNCqQUfLRvpKwddFKq+xZstw
O2fQKc1A3eGy6/g2py/Qph3mmTY+efoBuM3C6iRLEz2sWynqdjx7mBk46xz71p/b
r17FBGwl++JryTggnNS4HlepI2cS7lIN7Dt2paLCfRddzXFh4SDiuY1vq/Y9H/6u
3va2DSQKbNTX1MybZ4w0S79Whb6TwO/Px+6XPLAA6MESdV3Hc2zR4oXDNXtqQjdL
gICo3WgZAkNSJ6fFkHdl9RxpIUJdXFiRETBLGzH7fOAtLikET8XWkGdBSsyMSyXQ
P4EbGZ0Zzoh8eMcmr+HMwXnaowcGy+TsqC6bhlN4lif6l0gTObM=
=BHYy
-----END PGP SIGNATURE-----
