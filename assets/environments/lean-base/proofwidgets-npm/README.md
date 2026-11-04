# ProofWidgets fixed npm dependency materials

This directory covers all 387 non-root entries in the fixed ProofWidgets `package-lock.json`. The lock file is 172140 bytes with SHA-256 `3850e21b0823d6200db6da336ce1bd17a463db97ce314585ae47ed81a7327a7d`, matching ProofWidgets commit `b1436dc749e722c9920036b52cdc43b3451d0b69`.

Each `packages/<lock-path>/source.json` preserves the package name, fixed version, exact lock entry, official npm archive URL, SHA-512 integrity, archive SHA-256 and byte count, declared license, author, dev or platform-optional metadata, and notice provenance. Package archives and package binaries are not installed in this directory.

Notice files are organized by origin:

- `notices/original/`: 364 files extracted from exact fixed npm archives.
- `notices/supplementary/`: 44 same-project or fixed-source supplemental notices. Each `source.json` records its URL, ref and applicable version or current-text scope.
- `notices/vendored/`: seven cliui vendored-module notices with an explicit mapping in `packages/@isaacs/cliui/vendored-modules.json`. Six come from corresponding fixed-lock packages, and eastasianwidth uses the fixed cliui source license.
- `notices/standard/`: one SPDX MIT text explaining the declared license of build-only `is-reference`.

## Package-specific notice sources

`victory-vendor` 36.9.2 has no root LICENSE in its fixed archive, although its README declares MIT. Its 13 original lib-vendor D3 and Internmap notices remain separate. The project MIT text is supplemented from `victory@36.9.2` `package/LICENSE.txt`, with SHA-256 `34dee5fd5e5cc756efb5ad4d64652bce719bdf5e900ca5d7538253e737930bc4` and 1626 bytes, at `packages/victory-vendor/notices/supplementary/victory-36.9.2-LICENSE.txt`.

The cliui 9.0.0 archive has seven vendored module directories in both `dist/commonjs` and `dist/esm`. `packages/@isaacs/cliui/vendored-modules.json` maps all seven to their versions, fixed source, license URL, hash, and installed notice. `eastasianwidth` 0.3.0 uses the fixed cliui source `src/eastasianwidth/license`, with SHA-256 `94aa6016fb9d436508366433e9caba061443ca58f4c7eb515caec7badf90ae5a` and 1043 bytes. Its registry package.json and the cliui source function set support that version; the license is a fixed-source supplement, not an npm dist NOTICE.

The inventory covers the full lockfile, including 106 development dependencies and 26 platform-optional packages. These role fields describe how packages are installed or used during a build. Identifying which packages contribute to a generated JavaScript or WebAssembly bundle requires a separate review of that bundle and its build inputs. The records currently set `payload_linkage` to `not_asserted`; retain the complete notice and corresponding-source materials unless a bundle-specific review establishes a narrower set. The complete material set has 806 checksum entries in `SHA256SUMS`.

Obtain corresponding source from the pinned official URLs when required for redistribution, and retain the applicable notices for the containing image. Package installation and execution follow the upstream build instructions; this directory supplies source metadata and notices.
