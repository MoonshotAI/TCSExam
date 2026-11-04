-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: shadow
Binary: passwd, login, uidmap, libsubid4, libsubid-dev
Architecture: any
Version: 1:4.13+dfsg1-4ubuntu3.2
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Serge Hallyn <serge@hallyn.com>
Homepage: https://github.com/shadow-maint/shadow
Standards-Version: 4.6.1
Vcs-Browser: https://salsa.debian.org/debian/shadow
Vcs-Git: https://salsa.debian.org/debian/shadow.git -b master
Testsuite: autopkgtest
Testsuite-Triggers: augeas-tools, libnss-extrausers
Build-Depends: debhelper-compat (= 13), gettext, libcrypt-dev, libpam0g-dev, quilt, xsltproc <!nodoc>, docbook-xsl <!nodoc>, docbook-xml <!nodoc>, libxml2-utils <!nodoc>, libselinux1-dev [linux-any], libsemanage-dev [linux-any], itstool <!nodoc>, bison, libaudit-dev [linux-any]
Package-List:
 libsubid-dev deb libdevel optional arch=any
 libsubid4 deb libs optional arch=any
 login deb admin required arch=any essential=yes
 passwd deb admin required arch=any
 uidmap deb admin optional arch=any
Checksums-Sha1:
 521490d181c42fd2d9c19e7358a8b035e1e0db18 1811752 shadow_4.13+dfsg1.orig.tar.xz
 da5bd7f8055fa8a755a7c7a62011b8099c3ce4f5 96392 shadow_4.13+dfsg1-4ubuntu3.2.debian.tar.xz
Checksums-Sha256:
 a8bb3a2aceff1cbe39d0f50687dcc1d7e7be0516a9d954d8e2eedb93f5906207 1811752 shadow_4.13+dfsg1.orig.tar.xz
 ff01a3e94111ca8c4dca097ebe54edbee912cbdeba042c214bfa4c34e7839f61 96392 shadow_4.13+dfsg1-4ubuntu3.2.debian.tar.xz
Files:
 8eff6d434a14a5db7ecb10a3228c45b4 1811752 shadow_4.13+dfsg1.orig.tar.xz
 0061f5ec056b1e861829423909495be1 96392 shadow_4.13+dfsg1-4ubuntu3.2.debian.tar.xz
Original-Maintainer: Shadow package maintainers <pkg-shadow-devel@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQGzBAEBCgAdFiEELia6gbrGuCtTbip9+b5w1tgxniEFAmZYnxUACgkQ+b5w1tgx
niFIyAwAl1R0Kg3W58NftxzAyF9+F4bUefZJgWaO/rU/vm0iPQpJ4vUgeH9UIyuS
t7TZQXa/+Clq8fxPc4fUPpd49qC8WV7xV19wv4fLqauLCvn28Yhh/IVNOwDBAgtW
UlIzEXoW2thyCGtgYrWiVbXVl6ajXSYPVbRtjK7Fsuq9wjojq2gV2FD7p7G8ENc3
+wnRZOZbC3tKZsPgWjjjkHlYFzBQxG6Kpu2BTf1APWBKItLrNCYWoc8h9jlWe5uA
7NTexBxwaIBfhkUE7maA/Ws1EGJu618zk55PJK3JDh8j8iNm9XPOqZDNFkoybNdr
rxEWspNFHDui1b2YTAa/h5taVnVaCi4IM9nwROKuKrovUDtsqZ0HwLVc+ntsmmG9
AJxjGYSQmqjOhwTnEcWg1RGp47rO1dQE7PkNvwiV0IOS0eh3iw3xAIWCvuOkXqDO
6NM+3EKgtMzGx6LuktFvZft8YjSzDVgU+y47QIaW7iag7Rfxw+SNlZCr/RnQPwQT
6NS7Otyg
=okU/
-----END PGP SIGNATURE-----
