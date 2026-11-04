# Graphviz corresponding-source offer

The Graphviz 15.0.0 program embedded in the ProofWidgets browser payloads is available under EPL-2.0. The complete corresponding source for Graphviz, the fixed wrapper source, the wrapper's Graphviz modifications, and the build rules accompany this image under `/usr/share/doc/tcsexam/graphviz-epl/`. Recipients can obtain these source materials directly from that directory without network access.

## Complete source archives

| Component | Installed archive | Official origin | Bytes | Verified SHA-256 |
|---|---|---|---:|---|
| Graphviz 15.0.0 | `source/graphviz-15.0.0.tar.gz` | https://gitlab.com/graphviz/graphviz/-/archive/15.0.0/graphviz-15.0.0.tar.gz | 41113527 | `dfa5be5c311f760aa9c88273c8f8101bb11f50b0de8b29bbd54acff3adc2d563` |
| `hpcc-js-wasm` commit `8b86e2f83cc7344aca44fb3d8aa29a227358c5c4` | `source/hpcc-js-wasm-8b86e2f83cc7344aca44fb3d8aa29a227358c5c4.tar.gz` | https://github.com/hpcc-systems/hpcc-js-wasm/archive/8b86e2f83cc7344aca44fb3d8aa29a227358c5c4.tar.gz | 455080 | `5443207dda2c30581e0632c8add206fcae3906f5faf20d4a0808499934743ee6` |

The Graphviz archive also has SHA-512 `d69e2dd7b5127650b6e09de92508a84886d52d5dfd1eacf9e6abb797ca231db3c1b12546c7b8561e311150cd62be8dfea689021b7d139ffcdb3d4e16da670352`, exactly matching the value fixed in the wrapper's `vcpkg-overlays/graphviz/portfile.cmake`. The wrapper archive has SHA-512 `1a195429ba1d9d47803a78fc700c601ffcbd340d42b3c753f0f2a77cec4782768844b658227543bad7597ea5af553590c401a25ccc1aefea31a6b04f19e16a63`.

The source preparation command verifies the complete archives against the declared sizes and hashes. The Graphviz `LICENSE` member is installed as `EPL-2.0.txt`; the wrapper `LICENSE` member is installed as `WRAPPER-APACHE-2.0.txt`.

## Modifications and build rules

The wrapper archive is the fixed source for `@hpcc-js/wasm` 2.34.2. npm's version metadata identifies commit `8b86e2f83cc7344aca44fb3d8aa29a227358c5c4` as its `gitHead`.

The wrapper's `vcpkg-overlays/graphviz/portfile.cmake` replaces Graphviz's top-level `CMakeLists.txt` and `cmake/config_checks.cmake` with files from the overlay. It also replaces the `GVPLUGIN_CURRENT` and `GVPLUGIN_REVISION` substitutions described in that portfile. The exact files are present in the wrapper archive and as readable copies under `build-rules/vcpkg-overlays/graphviz/`.

The wrapper C++ entry point and support sources are under `build-rules/packages/graphviz/src-cpp/`. The wrapper build files select Emscripten SDK 6.0.0 and vcpkg 2026.06.01. Their official project locations are:

- https://github.com/emscripten-core/emsdk
- https://github.com/microsoft/vcpkg

For a source rebuild, extract the wrapper archive into a writable directory and follow `build-rules/README.md`. The principal commands recorded by that fixed source are `npm ci`, `npm run install-build-deps`, and `npm run build`. The complete archive includes the build scripts and presets. Install the specified build tools and retain their applicable source and license materials alongside this Graphviz-specific archive set.

## Verification

From the installed directory, run:

```bash
cd /usr/share/doc/tcsexam/graphviz-epl
sha256sum -c SHA256SUMS
```

`source-manifest.json` records the same versions, official URLs, archive sizes, and hashes in machine-readable form. Use the separate browser-component and npm inventories for the sources and notices of the image's other components.
