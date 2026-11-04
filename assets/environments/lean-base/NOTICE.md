# Third-party notices for the Lean environment

This is the entry point for the component license and source materials installed under `/usr/share/doc/tcsexam/`.

- [mathlib and Lake component licenses](lean-components/README.md): nine per-component license texts, fixed commits, public source locations, and independent-NOTICE search results, installed at `/usr/share/doc/tcsexam/lean-components/`.
- [Graphviz EPL-2.0 materials](graphviz-epl/README.md): the Graphviz license, corresponding-source offer, complete source archives, wrapper modifications, build rules, official source URLs, and verified hashes, installed at `/usr/share/doc/tcsexam/graphviz-epl/`.
- [Browser nested-component materials](browser-components/README.md): Expat, Emscripten runtime notices, and Penrose optimizer with its exact Cargo.lock notice superset, including payload and linkage scope, installed at `/usr/share/doc/tcsexam/browser-components/`.
- [ProofWidgets fixed npm materials](proofwidgets-npm/README.md): all 387 fixed-lock dependencies with per-package source metadata, 364 original notices, 44 supplementary notices, six reused cliui vendored notices, and one clearly labeled SPDX standard text, installed at `/usr/share/doc/tcsexam/proofwidgets-npm/`.

The ProofWidgets browser payloads contain Graphviz 15.0.0. Graphviz is licensed under the Eclipse Public License 2.0 (EPL-2.0). The `@hpcc-js/wasm` wrapper has a separate Apache-2.0 license; that wrapper license does not apply to Graphviz.

The browser and npm directories preserve notices and exact source locations without treating every build or lockfile dependency as linked payload code. Other image software retains its own licenses and notice requirements. Preserve corresponding source and notices when distributing a containing image; the dependency inventory does not assert that every build dependency is linked into the payload.
