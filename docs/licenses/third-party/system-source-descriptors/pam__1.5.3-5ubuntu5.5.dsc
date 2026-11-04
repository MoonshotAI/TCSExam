-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: pam
Binary: libpam0g, libpam-modules, libpam-modules-bin, libpam-runtime, libpam0g-dev, libpam-doc
Architecture: any all
Version: 1.5.3-5ubuntu5.5
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Steve Langasek <vorlon@debian.org>
Homepage: http://www.linux-pam.org/
Standards-Version: 4.6.2
Vcs-Git: https://code.launchpad.net/~ubuntu-core-dev/ubuntu/+source/pam/+git/pam
Testsuite: autopkgtest
Testsuite-Triggers: python3-pam
Build-Depends: debhelper-compat (= 13), dh-exec, flex, libcrypt-dev, libdb-dev, libselinux1-dev [linux-any], libsystemd-dev [linux-any] <!stage1>, po-debconf, autopoint, libaudit-dev [linux-any] <!stage1>, pkg-config, libfl-dev, libfl-dev:native, docbook-xsl-ns, docbook5-xml, xsltproc, libxml2-utils, w3m
Build-Conflicts: libdb4.2-dev, libxcrypt-dev
Build-Conflicts-Indep: fop
Package-List:
 libpam-doc deb doc optional arch=all
 libpam-modules deb admin required arch=any
 libpam-modules-bin deb admin required arch=any
 libpam-runtime deb admin required arch=all
 libpam0g deb libs optional arch=any
 libpam0g-dev deb libdevel optional arch=any
Checksums-Sha1:
 b27ea4def098bf3e4f277d6c78d42067e912cc1f 1020076 pam_1.5.3.orig.tar.xz
 861f4d7c17b9198dde470417506c2cefbeae5e63 204688 pam_1.5.3-5ubuntu5.5.debian.tar.xz
Checksums-Sha256:
 7ac4b50feee004a9fa88f1dfd2d2fa738a82896763050cd773b3c54b0a818283 1020076 pam_1.5.3.orig.tar.xz
 391da0d96481d5df4ee3952d8cac5a1496ff65fcb5e76f62caae8fdc2e866b44 204688 pam_1.5.3-5ubuntu5.5.debian.tar.xz
Files:
 a913bd5fbf9edeafaacf3eb1eb86fd83 1020076 pam_1.5.3.orig.tar.xz
 5aa83d52d77df2889bafed5b9872080c 204688 pam_1.5.3-5ubuntu5.5.debian.tar.xz
Debian-Vcs-Browser: https://salsa.debian.org/vorlon/pam
Debian-Vcs-Git: https://salsa.debian.org/vorlon/pam.git
Original-Maintainer: Sam Hartman <hartmans@debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmjID3wACgkQZWnYVadE
vpNwiw//aYoUsZdaruvZaggcdKD+Qv+KKS3lxYWQ3ElK320fBcifmRlihWx2AxoW
kmu8hz5j1kETd97wyq2c5fLwz9kMucTZfJ9NEEomnOgGArNB96PGMko+SI+DIZyF
/ElE3HW5gJudoAnlxLTicgUBm3dbpQDXt5nmYUWXHBSVjy6icFrLWBA2UWiNKGGC
66HUHQtoERpXqRyNmoKuBurityqnPsZho/mo/IHYBYZ+KA1dhS1O6ICa7SAuFC7z
aaFAwIOeVnHVFi7uIgIGs12rd/15ZYZmp1sn+HdgBJ/dv1NrhH5+jFWcbPYJ7jl0
Od/8H0KkrImsKYk5bQ06BSfiv1brHC+fYTGR0dXFdoEvhi9rDjTrR5tI5owiv8or
TptfCj2GhAwdCxLL5qQInNfannfVT/dEaVxVXcaM2XyOn1kMJuPd0lMM1lqXP8Hm
focHyed8VsOsN/5nvkCCKTxZYovhAhMyy1aBr7qoi3V9stSLkNHNejFhn24hLSTy
racRG+kxsVgyvCTherlR/zxYEmOvFECffhXuHrZFi/pCXI+6ouE7xXuCW2+ma484
cAV2tlC9SfPFcm9M93Jhko2+cQYekWugtwQK7fCWJz0ZIQIkU3v59fJpv6E4kpQj
tbJ0O06/HZx5wOx3aB0H3ntIahwWgSjtBBqRLwKltgBzCpGb3kU=
=Urz+
-----END PGP SIGNATURE-----
