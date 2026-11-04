-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: libassuan
Binary: libassuan0, libassuan-dev, libassuan-mingw-w64-dev
Architecture: any all
Version: 2.5.6-1build1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders:  Eric Dorland <eric@debian.org>, Daniel Kahn Gillmor <dkg@fifthhorseman.net>,
Homepage: https://www.gnupg.org/related_software/libassuan/index.html
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/libassuan
Vcs-Git: https://salsa.debian.org/debian/libassuan.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, gcc-mingw-w64-i686, gcc-mingw-w64-x86-64, pkg-config, wine32, wine64
Build-Depends: debhelper-compat (= 13), libgpg-error-dev (>= 1.33)
Build-Depends-Indep: libgpg-error-mingw-w64-dev, mingw-w64
Package-List:
 libassuan-dev deb libdevel optional arch=any
 libassuan-mingw-w64-dev deb libdevel optional arch=all
 libassuan0 deb libs optional arch=any
Checksums-Sha1:
 b1e8754dbf89b3a3eb175f5df75048dbca1fce57 577012 libassuan_2.5.6.orig.tar.bz2
 8fe2173af54e7e72331a35deb933a981b4f3c85d 228 libassuan_2.5.6.orig.tar.bz2.asc
 5dc98e4f6b592eef917ba5b262ca596392438b21 14412 libassuan_2.5.6-1build1.debian.tar.xz
Checksums-Sha256:
 e9fd27218d5394904e4e39788f9b1742711c3e6b41689a31aa3380bd5aa4f426 577012 libassuan_2.5.6.orig.tar.bz2
 a1be6f5611de2f563a904c539e0415dd5823d9e1c4c0c1071418e7412174eaea 228 libassuan_2.5.6.orig.tar.bz2.asc
 f6e12195adc071a935556ccea239a64cd305ce667dde4ce9a11691e41278a1c4 14412 libassuan_2.5.6-1build1.debian.tar.xz
Files:
 9c22e76168675ec996b9d620ffbb7b27 577012 libassuan_2.5.6.orig.tar.bz2
 cc0b472a26ba33b6aa12e8ab9a6db6c3 228 libassuan_2.5.6.orig.tar.bz2.asc
 1a881485a022b159181d31686d2ced99 14412 libassuan_2.5.6-1build1.debian.tar.xz
Original-Maintainer: Debian GnuPG-Maintainers <pkg-gnupg-maint@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQJHBAEBCgAxFiEET7WIqEwt3nmnTHeHb6RY3R2wP3EFAmYUFRMTHGp1bGlhbmtA
dWJ1bnR1LmNvbQAKCRBvpFjdHbA/ccbqEACMrefTrgj742sZATT9Yz3orv2vN9ym
/DuaqtLV2ktIkiW0cgvqRHjxMoiTSWF1Si6N81lUdPAB+a5f4qELDHX08ZxUDa06
4MAyLkK1w7GgiQFR6lQyAOSze4GwCi2LqG2Vo0Z1sjv9CRSsz1a5kajsUpIFqyBV
N0aRDrOOk1cioeKAexgl4iEK9lu+9+amne55Df4AMwixfd/rMZRouMi3QfroM+xz
WJEt1VVrvIBuY40F084zc+PQ2n4z9jcG2/OlK23uhk/r0uc5IoaEgD1Vhe3aNQgV
3lDZanqNw6sM4Slb8dX60MeUHEIzRp7XaJo/egNLgrBQP0ixZ5/xFtLLJvzoxtOL
6KhAwwmulisLI9LxGNRM7nZIk7bubWYsaZ7GpIH9O1KVVAnFdXbGE9YSFMH0JBnK
Odclf1w86C0ovt+dmbI4QYTiYOftjA6YUhiB5ZqSRfs+jpStdHr29nuHTZaStLCW
gZQ8QVnWEx77uYtP71pNYcax367UEzZIyJTSWFxpKIv8kVNfomW3cyaNvksUPkj8
Qdr1MSQEVokj+vN1AHOxTg7n/AH1M4CI2937SRXnxP+JAPVkuXcOaJRhmIPk/8+d
46V0YP5jJIfJTu/MSV8IdqgwA3008TaaWo2jmCTmAqCMFY6x8ppREqcmK707elPI
A1v0iH4POiAxhg==
=hKmf
-----END PGP SIGNATURE-----
