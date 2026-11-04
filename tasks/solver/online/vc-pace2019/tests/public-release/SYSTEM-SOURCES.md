# System dependency source and notice coverage

This document describes the accompanying system source material for the public VC judge image. It is for recipients checking license notices or obtaining the source corresponding to installed system binaries.

## Included material

The candidate includes the following files under `/usr/share/tcsexam/source-packages/`:

- `debian/`: 278 files from 86 exact Debian source versions, totaling 546,497,313 bytes. These cover all 151 installed Debian binary packages.
- `python/Python-3.12.13.tar.xz`: the exact Python source archive selected by the original image's `PYTHON_VERSION` and `PYTHON_SHA256` configuration.
- `python-distributions/pip-25.0.1.tar.gz`: the source distribution for the only installed Python package, pip 25.0.1.

The total included source payload is 569,249,871 bytes. `manifest.json` records every source package, installed binary package mapping, file name, byte count, SHA-256, and acquisition scope.

All 151 installed Debian packages also retain their existing `/usr/share/doc/<package>/copyright` files; none was missing during the image audit. Adding source archives does not replace those notices.

## Verification performed

Every Debian `.dsc` was checked for the exact `Source` and `Version` of the installed binaries and for coverage of the corresponding `Package-List` entries. Every listed source component was re-hashed and checked against the `.dsc` `Checksums-Sha256` values. The candidate contains the verified source files themselves, not only download locations.

Repository metadata authentication covered 78 source packages acquired through apt. Eight packages were retrieved as fixed files from the official Debian snapshot because the mirror no longer offered the exact version or apt selected a newer version: audit, base-files, brotli, gzip, perl, sqlite3, tzdata, and util-linux. Those eight received the same Source, Version, Package-List, size, and SHA-256 checks. Their acquisition used HTTPS and the `20260713T000000Z` Debian snapshot retained in the original image configuration.

The signed `.dsc` files are retained, but their OpenPGP signatures were not independently verified. This limitation is recorded in `manifest.json`.

The Python archive SHA-256 is `c08bc65a81971c1dd5783182826503369466c7e67374d1646519adf05207b684`, matching the official Python 3.12.13 Docker build definition. The pip archive SHA-256 is `88f96547ea48b940a3a385494e181e29fb8637898f88d88737c5049780f196ea`, matching the fixed PyPI metadata.

## Using the source

No network is required to read or unpack the included source. For example, on a system with `dpkg-dev` installed:

```bash
cd /tmp
dpkg-source -x /usr/share/tcsexam/source-packages/debian/<package>.dsc
```

The GPL-3.0 `vc_validate` source and its fixed public build instructions are separate under `/opt/vc/corresponding-source/` and `/opt/vc/BUILD-vc_validate.md`. Project-authored scripts remain readable at their original paths, with the project LICENSE and NOTICE under `/licenses/`. Public VC instance attribution and the complete CC BY 4.0 text are under the same directory.
