-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: bzip2
Binary: libbz2-1.0, libbz2-dev, bzip2, bzip2-doc
Architecture: any all
Version: 1.0.8-5.1build0.1
Maintainer: Anibal Monsalve Salazar <anibal@debian.org>
Uploaders: Santiago Ruano Rincón <santiago@debian.org>, Anthony Fok <foka@debian.org>
Homepage: https://sourceware.org/bzip2/
Standards-Version: 4.6.0
Vcs-Browser: https://salsa.debian.org/debian/bzip2
Vcs-Git: https://salsa.debian.org/debian/bzip2.git
Testsuite: autopkgtest
Testsuite-Triggers: @builddeps@, build-essential
Build-Depends: debhelper-compat (= 13)
Build-Depends-Indep: texinfo, docbook-xml, docbook2x, xsltproc
Package-List:
 bzip2 deb utils standard arch=any
 bzip2-doc deb doc optional arch=all
 libbz2-1.0 deb libs important arch=any
 libbz2-dev deb libdevel optional arch=any
Checksums-Sha1:
 bf7badf7e248e0ecf465d33c2f5aeec774209227 810029 bzip2_1.0.8.orig.tar.gz
 1e9e3b10aa0753a278157bdcb9126b29d4e32a06 26927 bzip2_1.0.8-5.1build0.1.debian.tar.bz2
Checksums-Sha256:
 ab5a03176ee106d3f0fa90e381da478ddae405918153cca248e682cd0c4a2269 810029 bzip2_1.0.8.orig.tar.gz
 0ac0bd78fc0a7f6311a0bb62e81037ec920eb29e315261032ee84c4018e600f3 26927 bzip2_1.0.8-5.1build0.1.debian.tar.bz2
Files:
 67e051268d0c475ea773822f7500d0e5 810029 bzip2_1.0.8.orig.tar.gz
 878f5ae94ca753f4f2e5ca0a7a6d4afc 26927 bzip2_1.0.8-5.1build0.1.debian.tar.bz2
-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEVovyKmYzfL/Jprm3LIPbyOm9DjcFAma1gkcACgkQLIPbyOm9
DjeGow//UuEbpmfLQEGxZiUoM19/qwd2dStTLfTl6d81adwZLEsEWRm76RWg3ZUB
5rkXg1jN4IbehZdJQ2MUcoxC4+ivG0elYwNLMQmpmsfUe/ySpRScTAKUrFB98sKd
luu9qoEbPULO35SlsUt7hwWtS/4SG7dsztznyFmHmrhFR1igh9M01qY+AQFm7P+l
G2EzFYqXirt0vMXoKsrD2NToR4XSmglP4Qvh+zLZa39a1LxMAcay8bezCEwsHyec
JfQhxsgZ14QwA0gfmIJF2U4kukhy06tMqE3kY9aUkdTKDM+rC+F1U4mAGvHVRl/Q
cdQaxi6titETjcVjiHlS1oJTnuyRGRTv6z+dAnd+SN8gxud/MAas/bl/KmQQ2/FA
5JCR01FcZMEey3MjEozJoeLhE+sf6jC6dWj8pyKiWt5AvH0rWDRvE3PhmFj7GGD/
WHxu3WDKEHw/MnAF2Ffj05NkwtqpQTLZcdnEPB7k7ivrSO6GH8RMZULR9f7zX1q4
2ruVEGQaPAzfGK58dab/+Ymop/9NInkuDcz0msF4acGE6lbUCDi5bvnkW9iVQgp9
DTIRyTnhyORjipANTcJcsEUathgYcuXofjv1mbwIARIFdXtOIzmSm4atca4UKVWN
gbto+AuiwZfQAX3k0mgiEe0pfIyIymC0p4Bp6Srqgf9l8eLbjsc=
=htbw
-----END PGP SIGNATURE-----
