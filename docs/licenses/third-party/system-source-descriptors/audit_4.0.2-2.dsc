-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: audit
Binary: auditd, libauparse0t64, libauparse-dev, libaudit1, libaudit-common, libaudit-dev, python3-audit, golang-redhat-audit-dev, audispd-plugins
Architecture: linux-any all
Version: 1:4.0.2-2
Maintainer: Laurent Bigonville <bigon@debian.org>
Homepage: https://people.redhat.com/sgrubb/audit/
Standards-Version: 4.7.0
Vcs-Browser: https://salsa.debian.org/debian/audit
Vcs-Git: https://salsa.debian.org/debian/audit.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, pkg-config, python3-all
Build-Depends: dpkg-dev (>= 1.22.5), debhelper-compat (= 13), dh-python <!nopython>, libcap-ng-dev, libkrb5-dev, libldap2-dev <!pkg.audit.noldap>, libwrap0-dev, linux-libc-dev (>= 5.9~), python3-all-dev:any <!nopython>, libpython3-all-dev <!nopython>, swig
Build-Depends-Indep: golang-any
Package-List:
 audispd-plugins deb admin optional arch=linux-any profile=!pkg.audit.noldap
 auditd deb admin optional arch=linux-any
 golang-redhat-audit-dev deb golang optional arch=all
 libaudit-common deb libs optional arch=all
 libaudit-dev deb libdevel optional arch=linux-any
 libaudit1 deb libs optional arch=linux-any
 libauparse-dev deb libdevel optional arch=linux-any
 libauparse0t64 deb libs optional arch=linux-any
 python3-audit deb python optional arch=linux-any profile=!nopython
Checksums-Sha1:
 fcb0bdecdaa649d1e688196713a824c332f37d65 1198769 audit_4.0.2.orig.tar.gz
 e0a6f0b7b3a63e273cd7db8a2a8a8f737b4af7f9 19228 audit_4.0.2-2.debian.tar.xz
Checksums-Sha256:
 d5d1b5d50ee4a2d0d17875bc6ae6bd6a7d5b34d9557ea847a39faec531faaa0a 1198769 audit_4.0.2.orig.tar.gz
 33030d53299c57cda73e9e45813b8488f9bc3ad8992aef0b740afabbf66a2ba2 19228 audit_4.0.2-2.debian.tar.xz
Files:
 e21dfdc5d09b5e9bc66b6b8b0deddfb7 1198769 audit_4.0.2.orig.tar.gz
 e2da389c42e55fd1c40d7fcc6ae32d70 19228 audit_4.0.2-2.debian.tar.xz

-----BEGIN PGP SIGNATURE-----

iQFFBAEBCgAvFiEEmRrdqQAhuF2x31DwH8WJHrqwQ9UFAmc2Z7MRHGJpZ29uQGRl
Ymlhbi5vcmcACgkQH8WJHrqwQ9WXmgf/SKH4i+kK9kC2+Xb0BHH8cGDvq+rbEj6f
S3+1c83Edx5DXbU9pViBEj8tVk0pYMRkKtB1BFjplZUnBiq0mn7lNqGRUCRatdPH
YSHNVFfai2Dy933AyxylLb0eXKSDMb783onDn8XDCrwdn1W09dyxBS/A3QQRdkIg
FFW6/jtzJmLJG8tk9jsX5D0qEFtudoDqIAL8iCTFdLr91Si8DRdnZWe2XqhxLZJQ
IaVejNvBtEPPbYxTyVNZB0V3vY8khA+PidG0rRs/tzDHjIOuMZjnbqmAAaIdrGR0
uiB8rwUvyTf7MYSOjY/i/RJMnHRNZ+ZIy5NlDXV0MSGbyYucefJTcw==
=CEF2
-----END PGP SIGNATURE-----
