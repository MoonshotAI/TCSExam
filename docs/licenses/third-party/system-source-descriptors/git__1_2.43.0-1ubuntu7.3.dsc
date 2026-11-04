-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: git
Binary: git, git-man, git-doc, git-cvs, git-svn, git-mediawiki, git-email, git-daemon-run, git-daemon-sysvinit, git-gui, gitk, gitweb, git-all
Architecture: any all
Version: 1:2.43.0-1ubuntu7.3
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
 7999894681c3c8ec60600fb8af535a4eb021c2bf 795448 git_2.43.0-1ubuntu7.3.debian.tar.xz
Checksums-Sha256:
 5446603e73d911781d259e565750dcd277a42836c8e392cac91cf137aa9b76ec 7382996 git_2.43.0.orig.tar.xz
 5bb363b59fda93816ec9ef34476e720b4f66f4b9947866bfaf414964be7dd4a7 795448 git_2.43.0-1ubuntu7.3.debian.tar.xz
Files:
 66a036a0442b8d159b0eff5a0fe0dc94 7382996 git_2.43.0.orig.tar.xz
 96d06ca7586b09a23e42c349ab29d99e 795448 git_2.43.0-1ubuntu7.3.debian.tar.xz
Original-Maintainer: Jonathan Nieder <jrnieder@gmail.com>

-----BEGIN PGP SIGNATURE-----

iQJTBAEBCgA9FiEELOLXZEFYQHcSWEHiyfW2m9Ldu6sFAmhmkOMfHGhsaWIua29y
emh5bnNreXlAY2Fub25pY2FsLmNvbQAKCRDJ9bab0t27q0lzD/sH3+T6dAmFcjA5
frSUR+Weolmv4y8BYgp6D1vFTWAexO01ZQUrIpcgcArFdndOZSNZyRNkEHBfhkx2
skvEpMD/Y6BThztfVMDjZa4+U0toCPNctSQYX5ed6g8Hn8QS+cjulXiLl6RpR4ho
WF5P82Iw3qTN8dKWixd3B1S8bVh5xYVt29B8usiHio/0Jyccn8IjOoGhiIys9LOK
UCaBomFZXz6mWqKFpVALu9r2ECPyHQQOsYSGgaITL0wTEhJ734ab2WwMN1OhHJ7z
EWiU+itOBSy1C3OoRAEY4YL113xdAF7gYNSG5qC3HVOhziZVN82b+nnW/3/mXZaT
FudCQNhP1ErUPQB4OD8Jf4hExFHWwO6C9B0OBqq/cNuMpqWWVelluIG0ED+XlBQ6
EoyOQF7M74KWjXeiuQQaVj6hCNF/TEr4F1nqX8Q1CpDKqEHgt3E92LnPQ69p4j1L
mjGcETw0STngUb812jzSxJ+jQgwV98Snfo6ECtyA7QMvXDOmWfFfEoZ0n6RmcW3H
02PlTuTHRlkYUGp77rvNClhwbfYBQmj26WwQLoOEX8wznhMSM52K2xUALo0L4JNn
FN6lEFRpqdU0r0qKNxMdDzGVI7jXsfS3TBY/6GD/fve/VGvov0z6zWLT3cj1fMW/
umUb48AyrwTe2i54v/zGRZRFq9jY/A==
=ugBi
-----END PGP SIGNATURE-----
