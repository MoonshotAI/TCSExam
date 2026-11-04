# Graphviz 15.0.0 EPL-2.0 materials

ProofWidgets commit `b1436dc749e722c9920036b52cdc43b3451d0b69` supplies generated browser files in the Lean image. Those files embed Graphviz 15.0.0 as WebAssembly with SHA-256 `b73447cdf82c85bc61be2ebb78f1ac17a70fb7567c9f739268d7542e88cc421c`.

Graphviz is licensed under EPL-2.0. The `@hpcc-js/wasm` 2.34.2 wrapper is separately licensed under Apache-2.0. The wrapper license does not cover Graphviz.

Start with [SOURCE-OFFER.md](SOURCE-OFFER.md) for the corresponding-source statement, verified archive hashes, official source URLs, and rebuild paths. The complete Graphviz and wrapper/build source archives accompany the image in `source/`; network access is not needed to obtain those source materials.

Contents:

- `EPL-2.0.txt`: the Graphviz license, extracted from the verified Graphviz archive.
- `WRAPPER-APACHE-2.0.txt`: the wrapper license, extracted from the verified wrapper archive.
- `SOURCE-OFFER.md`: how to obtain and inspect the corresponding source.
- `source-manifest.json`: machine-readable versions, URLs, byte counts, and hashes.
- `source/`: complete fixed source archives for Graphviz 15.0.0 and `hpcc-js-wasm` commit `8b86e2f83cc7344aca44fb3d8aa29a227358c5c4`.
- `build-rules/`: readable copies of the wrapper build rules, Graphviz wrapper C++ sources, and Graphviz overlay modifications from the same wrapper archive.
- `SHA256SUMS`: hashes for the installed files other than the checksum file itself.

These materials accompany the generated Graphviz JavaScript and WebAssembly. The separate browser-component and npm inventories provide sources and notices for other browser dependencies.
