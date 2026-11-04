-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: git
Binary: git, git-man, git-doc, git-cvs, git-svn, git-mediawiki, git-email, git-daemon-run, git-daemon-sysvinit, git-gui, gitk, gitweb, git-all
Architecture: any all
Version: 1:2.43.0-1ubuntu7.4
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Anders Kaseorg <andersk@mit.edu>
Homepage: https://git-scm.com/
Standards-Version: 4.3.0.1
Vcs-Browser: https://repo.or.cz/w/git/debian.git/
Vcs-Git: https://repo.or.cz/r/git/debian.git/
Build-Depends: libz-dev, gettext, libpcre2-dev | libpcre3-dev, libcurl4-gnutls-dev, libexpat1-dev, subversion [!i386], libsvn-perl [!i386], libyaml-perl, tcl, python3, libhttp-date-perl | libtime-parsedate-perl, libcgi-pm-perl, liberror-perl, libmailtools-perl, cvs, cvsps, libdbd-sqlite3-perl, unzip, libio-pty-perl, debhelper-compat (= 10), dh-exec (>= 0.7), dh-apache2, dpkg-dev (>= 1.16.2~)
Build-Depends-Indep: asciidoc (>= 8.6.10), xmlto, docbook-xsl
Package-List:
 git deb vcs optional arch=any
 git-all deb vcs optional arch=all
 git-cvs deb vcs optional arch=all
 git-daemon-run deb vcs optional arch=all
 git-daemon-sysvinit deb vcs optional arch=all
 git-doc deb doc optional arch=all
 git-email deb vcs optional arch=all
 git-gui deb vcs optional arch=all
 git-man deb doc optional arch=all
 git-mediawiki deb vcs optional arch=all
 git-svn deb vcs optional arch=all
 gitk deb vcs optional arch=all
 gitweb deb vcs optional arch=all
Checksums-Sha1:
 d34f8331e3dcd7d2beb2f4af3e3d6db50b8036f1 7382996 git_2.43.0.orig.tar.xz
 5830c6af3ecd3656bd3e88ff69467c0e23e1b102 796932 git_2.43.0-1ubuntu7.4.debian.tar.xz
Checksums-Sha256:
 5446603e73d911781d259e565750dcd277a42836c8e392cac91cf137aa9b76ec 7382996 git_2.43.0.orig.tar.xz
 da368dcd58b9889787e7448d907cfc7ac06536472f78421f91351eee71f6d74b 796932 git_2.43.0-1ubuntu7.4.debian.tar.xz
Files:
 66a036a0442b8d159b0eff5a0fe0dc94 7382996 git_2.43.0.orig.tar.xz
 49180110291982a4906edc1120b66ad9 796932 git_2.43.0-1ubuntu7.4.debian.tar.xz
Original-Maintainer: Jonathan Nieder <jrnieder@gmail.com>

-----BEGIN PGP SIGNATURE-----

iQJSBAEBCgA8FiEEtNElVmlvlJD9Tt9SD2QDvITYlW8FAmrSYdYeHGNoYXJsZXMu
Y29jaHJhbkBjYW5vbmljYWwuY29tAAoJEA9kA7yE2JVvjkQP/1X2ea68qBNsW1py
MANnoeXBdHEuAP++W8KfCumeIwhBzF4X2nHXAekjKxjCZAHBTGQpmnC8AgSNBVa2
HEivRx55rWFKlIgYG6RJGu7m0t+TWwg6XieCYyKqzZ+AajsInBYdLL27wB7KVfpk
/TY11MuC4C9/D/gCZXNmTkeIbGHE41uWzwUwASeogP+CcAHQ8R5KZszFhYnYQk4t
pqruWZWfpbfqcAKeUewZ4b1lO4e+pa/2Ra/tiuudV+fyZkWyzVDEruJgpiY96xIQ
O682OeI2RxeGfM8Zfnr+N02RA7EwL7bM2r87W9YVuog9CCXeaX99ka+4v8AivvxE
rT9VqRuSVrdzU9tcYa1k1ZEpcsj71MgD82Em9q8fjcMjy6PQj4M8DnA4ff1bZVaY
y56rv8ie9nPkOjWgJJyirm1bU9epwGL5YRAcfUaEh8Oe/vf34mzlqyR1orxn/THg
wSQngZKM+X3TOjOkgE1ySUk064SGRluaOHrSwz00+t4892mmRBGFTgpS6N8Qi/lL
GxOQmABhIttq9Zr/430THWvvEWY5uCSk6x+rPOQqpXYGuOPs57tmAuBJ/A7mDRCf
+5dkgC77bW6rNQve6CmS/RqcDJzYcIQysvPeQfo+eBGh4+CmLMrfY4FWRs2Tcx+Z
hV4WAM5qM4llyizT19VDoU2QiYna
=jpNO
-----END PGP SIGNATURE-----
