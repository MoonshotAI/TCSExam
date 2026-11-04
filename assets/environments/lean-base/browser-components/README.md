# Browser nested-component materials

This directory provides source locations and notices for Expat, Emscripten runtime components, and Penrose optimizer with the registry crates in its fixed Cargo.lock. It is for users inspecting or redistributing the Lean image's browser components.

The records identify both linked components and build dependencies. For redistribution, use the component records together with the actual image contents and the separate Graphviz source materials in `graphviz-epl/`.

## Expat

`expat/LICENSE` and `expat/source.json` preserve the Expat 2.8.1 MIT text and source location. The fixed vcpkg port selects this version; the Graphviz payload contains the linked Expat component.

## Emscripten

`emscripten/notices/` contains the Emscripten 6.0.0 license, musl COPYRIGHT, and libc++ LICENSE.TXT from the fixed build input. Retain applicable runtime notices when distributing generated WebAssembly; the component record covers build inputs and leaves the exact linked runtime subset unspecified.

## Penrose optimizer

`penrose-optimizer/LICENSE` preserves the Penrose MIT notice. `penrose-optimizer/build/` contains the fixed Cargo metadata. `penrose-optimizer/crates/` contains 46 per-crate directories with exact source URLs, archive hashes, license declarations, 77 original notice files, and 6 supplementary project notices.

The 46 crates cover the complete Cargo.lock, including build, host, and Windows-only dependencies. Their source records identify those roles. Supplementary notices are labeled separately from notices shipped in the crate archives.

## Obtain sources and retain notices

Use the exact public URLs and hashes in each component record to obtain its source archives. This directory stores source metadata and notices. Follow each component's license when distributing binaries or corresponding source.

The fixed ProofWidgets npm dependency set is documented in `proofwidgets-npm/`. Include the applicable source materials and notices for all components of the containing image.
