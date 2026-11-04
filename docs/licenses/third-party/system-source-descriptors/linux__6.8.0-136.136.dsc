-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 1.0
Source: linux
Binary: linux-headers-6.8.0-136, linux-tools-6.8.0-136, linux-cloud-tools-6.8.0-136, linux-libc-dev, linux-tools-common, linux-cloud-tools-common, linux-tools-host, linux-source-6.8.0, linux-doc, linux-bpf-dev, linux-image-unsigned-6.8.0-136-generic, linux-modules-6.8.0-136-generic, linux-modules-extra-6.8.0-136-generic, linux-headers-6.8.0-136-generic, linux-lib-rust-6.8.0-136-generic, linux-image-unsigned-6.8.0-136-generic-dbgsym, linux-tools-6.8.0-136-generic, linux-cloud-tools-6.8.0-136-generic, linux-buildinfo-6.8.0-136-generic, linux-modules-ipu6-6.8.0-136-generic, linux-modules-iwlwifi-6.8.0-136-generic, linux-modules-usbio-6.8.0-136-generic, linux-image-unsigned-6.8.0-136-generic-64k, linux-modules-6.8.0-136-generic-64k, linux-modules-extra-6.8.0-136-generic-64k, linux-headers-6.8.0-136-generic-64k, linux-lib-rust-6.8.0-136-generic-64k, linux-image-unsigned-6.8.0-136-generic-64k-dbgsym, linux-tools-6.8.0-136-generic-64k, linux-cloud-tools-6.8.0-136-generic-64k,
 linux-buildinfo-6.8.0-136-generic-64k, linux-modules-ipu6-6.8.0-136-generic-64k, linux-modules-iwlwifi-6.8.0-136-generic-64k, linux-modules-usbio-6.8.0-136-generic-64k, linux-image-unsigned-6.8.0-136-generic-lpae, linux-modules-6.8.0-136-generic-lpae, linux-modules-extra-6.8.0-136-generic-lpae, linux-headers-6.8.0-136-generic-lpae, linux-lib-rust-6.8.0-136-generic-lpae, linux-image-unsigned-6.8.0-136-generic-lpae-dbgsym, linux-tools-6.8.0-136-generic-lpae, linux-cloud-tools-6.8.0-136-generic-lpae, linux-buildinfo-6.8.0-136-generic-lpae, linux-modules-ipu6-6.8.0-136-generic-lpae, linux-modules-iwlwifi-6.8.0-136-generic-lpae,
 linux-modules-usbio-6.8.0-136-generic-lpae
Architecture: all amd64 armhf arm64 ppc64el s390x i386 riscv64
Version: 6.8.0-136.136
Maintainer: Ubuntu Kernel Team <kernel-team@lists.ubuntu.com>
Standards-Version: 3.9.4.0
Vcs-Git: git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble
Testsuite: autopkgtest
Testsuite-Triggers: @builddeps@, build-essential, fakeroot, gcc-multilib, gdb, git, python3
Build-Depends: gcc-13, gcc-13-aarch64-linux-gnu [arm64] <cross>, gcc-13-arm-linux-gnueabihf [armhf] <cross>, gcc-13-powerpc64le-linux-gnu [ppc64el] <cross>, gcc-13-riscv64-linux-gnu [riscv64] <cross>, gcc-13-s390x-linux-gnu [s390x] <cross>, gcc-13-x86-64-linux-gnu [amd64] <cross>, autoconf <!stage1>, automake <!stage1>, bc <!stage1>, bindgen-0.65 [amd64 arm64 armhf ppc64el riscv64 s390x], bison <!stage1>, clang-18 [amd64 arm64 armhf ppc64el riscv64 s390x], cpio, curl <!stage1>, debhelper-compat (= 10), default-jdk-headless <!stage1>, dkms <!stage1>, flex <!stage1>, gawk <!stage1>, java-common <!stage1>, kmod <!stage1>, libaudit-dev <!stage1>, libcap-dev <!stage1>, libdw-dev <!stage1>, libelf-dev <!stage1>, libiberty-dev <!stage1>, liblzma-dev <!stage1>, libnewt-dev <!stage1>, libnl-3-dev, libnl-genl-3-dev, libnuma-dev [amd64 arm64 ppc64el s390x] <!stage1>, libpci-dev <!stage1>, libssl-dev <!stage1>, libstdc++-dev, libtool <!stage1>, libtraceevent-dev [amd64 arm64 armhf ppc64el s390x riscv64] <!stage1>, libtracefs-dev [amd64 arm64 armhf ppc64el s390x riscv64] <!stage1>, libudev-dev <!stage1>, libunwind8-dev [amd64 arm64 armhf ppc64el] <!stage1>, makedumpfile [amd64] <!stage1>, openssl <!stage1>, pahole [amd64 arm64 armhf ppc64el s390x riscv64] | dwarves (>= 1.21) [amd64 arm64 armhf ppc64el s390x riscv64] <!stage1>, pkg-config <!stage1>, python3 <!stage1>, python3-dev <!stage1>, python3-setuptools <!stage1>, rsync [!i386] <!stage1>, rust-src [amd64 arm64 armhf ppc64el riscv64 s390x], rustc [amd64 arm64 armhf ppc64el riscv64 s390x], rustfmt [amd64 arm64 armhf ppc64el riscv64 s390x], uuid-dev <!stage1>, zstd <!stage1>
Build-Depends-Indep: asciidoc <!stage1>, bzip2 <!stage1>, python3-docutils <!stage1>, sharutils <!stage1>, xmlto <!stage1>
Package-List:
 linux-bpf-dev deb devel optional arch=amd64,armhf,arm64,i386,ppc64el,riscv64,s390x
 linux-buildinfo-6.8.0-136-generic deb kernel optional arch=amd64,armhf,arm64,ppc64el,s390x profile=!stage1
 linux-buildinfo-6.8.0-136-generic-64k deb kernel optional arch=arm64 profile=!stage1
 linux-buildinfo-6.8.0-136-generic-lpae deb kernel optional arch=armhf profile=!stage1
 linux-cloud-tools-6.8.0-136 deb devel optional arch=amd64,armhf profile=!stage1
 linux-cloud-tools-6.8.0-136-generic deb devel optional arch=amd64,armhf,arm64,ppc64el,s390x profile=!stage1
 linux-cloud-tools-6.8.0-136-generic-64k deb devel optional arch=arm64 profile=!stage1
 linux-cloud-tools-6.8.0-136-generic-lpae deb devel optional arch=armhf profile=!stage1
 linux-cloud-tools-common deb kernel optional arch=all profile=!stage1
 linux-doc deb doc optional arch=all profile=!stage1
 linux-headers-6.8.0-136 deb devel optional arch=all profile=!stage1
 linux-headers-6.8.0-136-generic deb devel optional arch=amd64,armhf,arm64,ppc64el,s390x profile=!stage1
 linux-headers-6.8.0-136-generic-64k deb devel optional arch=arm64 profile=!stage1
 linux-headers-6.8.0-136-generic-lpae deb devel optional arch=armhf profile=!stage1
 linux-image-unsigned-6.8.0-136-generic deb kernel optional arch=amd64,armhf,arm64,ppc64el,s390x profile=!stage1
 linux-image-unsigned-6.8.0-136-generic-64k deb kernel optional arch=arm64 profile=!stage1
 linux-image-unsigned-6.8.0-136-generic-64k-dbgsym deb devel optional arch=arm64 profile=!stage1
 linux-image-unsigned-6.8.0-136-generic-dbgsym deb devel optional arch=amd64,armhf,arm64,ppc64el,s390x profile=!stage1
 linux-image-unsigned-6.8.0-136-generic-lpae deb kernel optional arch=armhf profile=!stage1
 linux-image-unsigned-6.8.0-136-generic-lpae-dbgsym deb devel optional arch=armhf profile=!stage1
 linux-lib-rust-6.8.0-136-generic deb devel optional arch=amd64 profile=!stage1
 linux-lib-rust-6.8.0-136-generic-64k deb devel optional arch=amd64 profile=!stage1
 linux-lib-rust-6.8.0-136-generic-lpae deb devel optional arch=amd64 profile=!stage1
 linux-libc-dev deb devel optional arch=amd64,armhf,arm64,i386,ppc64el,riscv64,s390x
 linux-modules-6.8.0-136-generic deb kernel optional arch=amd64,armhf,arm64,ppc64el,s390x profile=!stage1
 linux-modules-6.8.0-136-generic-64k deb kernel optional arch=arm64 profile=!stage1
 linux-modules-6.8.0-136-generic-lpae deb kernel optional arch=armhf profile=!stage1
 linux-modules-extra-6.8.0-136-generic deb kernel optional arch=amd64,armhf,arm64,ppc64el,s390x profile=!stage1
 linux-modules-extra-6.8.0-136-generic-64k deb kernel optional arch=arm64 profile=!stage1
 linux-modules-extra-6.8.0-136-generic-lpae deb kernel optional arch=armhf profile=!stage1
 linux-modules-ipu6-6.8.0-136-generic deb kernel optional arch=amd64,armhf,arm64,ppc64el,s390x profile=!stage1
 linux-modules-ipu6-6.8.0-136-generic-64k deb kernel optional arch=arm64 profile=!stage1
 linux-modules-ipu6-6.8.0-136-generic-lpae deb kernel optional arch=armhf profile=!stage1
 linux-modules-iwlwifi-6.8.0-136-generic deb kernel optional arch=amd64,armhf,arm64,ppc64el,s390x profile=!stage1
 linux-modules-iwlwifi-6.8.0-136-generic-64k deb kernel optional arch=arm64 profile=!stage1
 linux-modules-iwlwifi-6.8.0-136-generic-lpae deb kernel optional arch=armhf profile=!stage1
 linux-modules-usbio-6.8.0-136-generic deb kernel optional arch=amd64,armhf,arm64,ppc64el,s390x profile=!stage1
 linux-modules-usbio-6.8.0-136-generic-64k deb kernel optional arch=arm64 profile=!stage1
 linux-modules-usbio-6.8.0-136-generic-lpae deb kernel optional arch=armhf profile=!stage1
 linux-source-6.8.0 deb devel optional arch=all profile=!stage1
 linux-tools-6.8.0-136 deb devel optional arch=amd64,armhf,arm64,ppc64el,s390x profile=!stage1
 linux-tools-6.8.0-136-generic deb devel optional arch=amd64,armhf,arm64,ppc64el,s390x profile=!stage1
 linux-tools-6.8.0-136-generic-64k deb devel optional arch=arm64 profile=!stage1
 linux-tools-6.8.0-136-generic-lpae deb devel optional arch=armhf profile=!stage1
 linux-tools-common deb kernel optional arch=all profile=!stage1
 linux-tools-host deb kernel optional arch=all profile=!stage1
Checksums-Sha1:
 27dce9d91afd9433620628fde58a686f5e53cebb 230060117 linux_6.8.0.orig.tar.gz
 e2f2bc4bea91a5222eeb5a0e5b985b57ed621c1f 8960450 linux_6.8.0-136.136.diff.gz
Checksums-Sha256:
 26512115972bdf017a4ac826cc7d3e9b0ba397d4f85cd330e4e4ff54c78061c8 230060117 linux_6.8.0.orig.tar.gz
 ccce6d47f36bc749d69a5faa41237c3269e5345d3852d6afe868a5629ac8c316 8960450 linux_6.8.0-136.136.diff.gz
Files:
 3ce3b99b065c7c0507b82ad0f330e2fd 230060117 linux_6.8.0.orig.tar.gz
 9b6936d520834ab9a542350b77044b1f 8960450 linux_6.8.0-136.136.diff.gz
Ubuntu-Compatible-Signing: ubuntu/4 pro/3 livepatch:2025 kmod:2025

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEOdMBrFJziXWR5e+rkdhqW2QaBCYFAmpFcQIACgkQkdhqW2Qa
BCaGJQ/9FUmrl4Xwq9uVAja1QLquGnkPPTZmbX20kC1ugWbqB8jfmcQSvPOWJbZm
hgfXZ0ulwQ+dYxOtLWzqSYI92E9r+0JOyh7VzE04ArarZNwDZMkJbw7Ypdg97i98
VFQU+DgClXgZn2ndb8w8hzuCzTxT75EsAz2+0+tFlNUaNRD1ZF7WQW5MsJZMgdwH
cAUVvdf7yB9+MTKAXY2hF8I8sYwsjsDVxLk6y2kluBZ+GO+B7LugdmICIN+Ceb0p
ou/a2qkHhAvv5smluNYC6j4anEdRgbE9X1XHYhiI/GlThCToeJlm4qYYC7kgjpyF
EsITpaRlMReXDdddFdJ3kR6cfNWaNTdaPDWDnwwr+vs6zhqYzGG24Mnmo+qKKFQe
yQCoQs9/0W9jsvcCAo5DkH1+DuwkABdmNVgS5NEiH/bj6LXt36dTyIOEeP2Idh/J
vQEDZv/OPoSUFPaFdveBCaSsMr9pxpxMjAiUu3L6qxCwLjmnZ5eOxg8r+6zNYJJf
Eao6+W65/uV3jhcfcENPeRuyBPhx5M6fCkFwaeQSDK7Z+St9TRsUyCY6dmuK0y2T
Bp7C2s6vwrrjF+nurzq7HBHKIm4e3JRFH7EUqUCkI9b0dvPN8vb4lzmX/GCCLAGl
rT8sVyWdsPUlI1ddns3XvFO3MLVjl7s6fAngoUzrKp6Cz+IV56E=
=EBaq
-----END PGP SIGNATURE-----
