-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA256

Format: 3.0 (quilt)
Source: rust-ripgrep
Binary: ripgrep
Architecture: any
Version: 14.1.0-1
Maintainer: Debian Rust Maintainers <pkg-rust-maintainers@alioth-lists.debian.net>
Uploaders:  Sylvestre Ledru <sylvestre@debian.org>
Homepage: https://github.com/BurntSushi/ripgrep
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/rust-team/debcargo-conf/tree/master/src/ripgrep
Vcs-Git: https://salsa.debian.org/rust-team/debcargo-conf.git [src/ripgrep]
Build-Depends: debhelper (>= 12), dh-cargo (>= 25), cargo:native, rustc:native (>= 1.70), libstd-rust-dev, librust-anyhow-1+default-dev (>= 1.0.75-~~), librust-bstr-1+default-dev (>= 1.7.0-~~), librust-grep-0.3+default-dev (>= 0.3.1-~~), librust-ignore-0.4+default-dev (>= 0.4.22-~~), librust-lexopt-0.3+default-dev, librust-log-0.4+default-dev (>= 0.4.5-~~), librust-serde-json-1+default-dev (>= 1.0.23-~~), librust-termcolor-1+default-dev (>= 1.4.0-~~), librust-textwrap-0.16-dev, asciidoc, bash-completion, xsltproc, docbook-xsl, librust-grep-dev (>= 0.2.8-3)
Package-List:
 ripgrep deb utils optional arch=any
Checksums-Sha1:
 714ed54b92e46f1fc6b85f6932d9f148df757f7a 216804 rust-ripgrep_14.1.0.orig.tar.gz
 113815cf85cfad746908e6ec7046ed52eba8d724 6476 rust-ripgrep_14.1.0-1.debian.tar.xz
Checksums-Sha256:
 d7bcbc3ac47a84bd5d0cefb27a53bbf3defb6867b97e526531fba2e564597fd8 216804 rust-ripgrep_14.1.0.orig.tar.gz
 ef547ec4a43542246c651727fb0b9745e00e50a30bbb8116fcf3098f245dc73c 6476 rust-ripgrep_14.1.0-1.debian.tar.xz
Files:
 2f4e207796c9cf98e709bed46444ae5f 216804 rust-ripgrep_14.1.0.orig.tar.gz
 3d3b9129c325b7c98b22a0a0ac81afd2 6476 rust-ripgrep_14.1.0-1.debian.tar.xz

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCAAdFiEEtg21mU05vsTRqVzPfmUo2nUvG+EFAmWhC1QACgkQfmUo2nUv
G+E32A//cBwlm6EjFJwVZAW0EH8RKW1J/CU3rNjj9ZYC7xsHf+bl3LXs6L7x/yIp
z6HDiKWicbIG3xSc0WjWS/GrsYQg+AQXrt19twiz6rxKAwJhSg+R43C+wv+A8A7v
SZo6BZp/ORoCk+Tg6tEZAxhDORymo+KaQ4+uXkNnS8BJyzRQyVeR35GOQcR7Ktd+
XOuLBTkDUzX3puE30zXmVLhek5aSH/mwFB2kwSxPKO2nXDTL0Z9h9bwXCsyneKyj
mjvY4r9/qQ/kxeGT4XRCTSTvPOIFZwFJQnsz2TaW5RiK+jRQ1F2h53zwpJm0puwC
Gbs/U1li331Drs+XPgH1/NXO0YIE/xD1h6iihWWsZm8phXEUb5J173SjTDnVayuG
A1RLXKUeiRqeN8pLWQvQGBCzsI+hLXRfc8wHcC2ETNt2WoKtgX2EqC5c6IHeTXsU
oVAxfudCrizdP5X+iEACZbD/plajwhkY/54aGvSZ9slY2lt7QcfdiBAcD7N7UlkE
+/oTiAI4i/9yvFIehAYFHD67INXznNefGVeVtRIM35urKnFAYdQFLjA49LQ7/tzy
tXm3eoUhmeKGxg6RUAEOimAJ/Z1d1c2IEtPx4rbxcmKrgH/ActxK9OgfKQWH5HCn
dwRoK4P4drKy0YraYr7ZGCenF85vOB8xq5NIDd10J22wgCHUa28=
=73KM
-----END PGP SIGNATURE-----
