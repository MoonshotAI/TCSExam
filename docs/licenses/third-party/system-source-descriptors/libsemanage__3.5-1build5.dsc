-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: libsemanage
Binary: libsemanage-common, libsemanage2, libsemanage-dev, ruby-semanage, python3-semanage, semanage-utils
Architecture: linux-any all
Version: 3.5-1build5
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Laurent Bigonville <bigon@debian.org>, Russell Coker <russell@coker.com.au>
Homepage: https://selinuxproject.org
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/selinux-team/libsemanage
Vcs-Git: https://salsa.debian.org/selinux-team/libsemanage.git
Build-Depends: bison, debhelper-compat (= 13), dh-sequence-python3 <!nopython>, dh-sequence-ruby <!noruby>, file, flex, gem2deb (>= 0.5.0~) <!noruby>, libaudit-dev, libbz2-dev, libcunit1-dev <!nocheck>, libpython3-all-dev <!nopython>, libselinux1-dev (>= 3.5), libsepol-dev (>= 3.5), pkg-config, python3-all-dev:any <!nopython>, secilc (>= 3.5) <!nocheck>, swig <!nopython> <!noruby>
Package-List:
 libsemanage-common deb libs optional arch=all
 libsemanage-dev deb libdevel optional arch=linux-any
 libsemanage2 deb libs optional arch=linux-any
 python3-semanage deb python optional arch=linux-any profile=!nopython
 ruby-semanage deb ruby optional arch=linux-any profile=!noruby
 semanage-utils deb admin optional arch=all
Checksums-Sha1:
 7dfb7935f03d08640a3afc5107d8e29405909a91 185060 libsemanage_3.5.orig.tar.gz
 eff5a11fbfa76b2f19ac2c118e8e6858e8863bf1 981 libsemanage_3.5.orig.tar.gz.asc
 f84f70a1623aa739cebe65e067f79697c22467da 30188 libsemanage_3.5-1build5.debian.tar.xz
Checksums-Sha256:
 f53534e50247538280ed0d76c6ce81d8fb3939bd64cadb89da10dba42e40dd9c 185060 libsemanage_3.5.orig.tar.gz
 f9126c861c666f3308b60cea4405c5e686a056113ca3cbd0a5b0e4af7600c8f5 981 libsemanage_3.5.orig.tar.gz.asc
 522654c2f5e0f508ce7c82f3c58cd394e1b9386226a2a6ac917e7fed9d8895b7 30188 libsemanage_3.5-1build5.debian.tar.xz
Files:
 71c5603b835fb0246b12236a07b4cb7b 185060 libsemanage_3.5.orig.tar.gz
 0c884025d0770e053b9245f93df2ff83 981 libsemanage_3.5.orig.tar.gz.asc
 3a861c42bb3794b556333f6d4cdd7b90 30188 libsemanage_3.5-1build5.debian.tar.xz
Original-Maintainer: Debian SELinux maintainers <selinux-devel@lists.alioth.debian.org>
Ruby-Versions: all

-----BEGIN PGP SIGNATURE-----

iQJOBAEBCgA4FiEErEg/aN5yj0PyIC/KVo0w8yGyEz0FAmYIx3UaHHN0ZXZlLmxh
bmdhc2VrQHVidW50dS5jb20ACgkQVo0w8yGyEz22wRAAzpo6pUPgfWBqRyjFrh0y
LkA6cO1Hdu07HZFtxHLK3i4ysBsOxDZ4nKkVCsBJXPRAVlOQVV9Bxv4uyWy0crs5
kxNY6KV0Hfn1IKdRwI1LQjrkcuGGeJRiuASVrmhX/OOB/NZDZmMGcVZAFnIgUsc+
iI2L8ku/zdhjXmoS0SiFLMNveaJHmylIC3DAdggLmM9JgGCi7XC3Oh35HtekrDls
pNQqSG2LX2DM01s6bPy6Gy20iJ8qCbtXvB/RR7sJcszQQkg031Fwx01SYZ6bQBFj
eyeMD15YtfXlD5Ubb5uyH4SjmVj2HeP3JeE1W7AkTf+hqLhMoLxu8Tgg+ECAT9S2
DV71cLzxj3M5Bt3c7Q5o2BuEA1jlvA4oQhuMy5Ewmw48ZWfOq+/udm5yCrY+tVz2
01ZgK9FRaGITu8xGVc0Eltv2sMeiqjFg83mHmM8RH/tpHlbMPzt+GwOha+/I+MlJ
AnOh6SsJqSe3RScK9RLprSBFxLL7x3eMTI03gQpdjoa1kB6JwFMO9tUjjfmqx8CL
bEYUDV4IfvvE+p2Y1dsULuBGTkWbmgwqDeQ05yPf5oAmpGEFA5C0FldPi9l7AV/l
e92/gqQ9LWiS0IU8IMVe/+4qZItd/L+ys3O8lUVlMWqYLha5eqe0PB5AZqjdRB8U
EaBLPfiXKq9M/yvw9TiVv1Y=
=NzHN
-----END PGP SIGNATURE-----
