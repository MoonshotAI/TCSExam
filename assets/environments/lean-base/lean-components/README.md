# mathlib and Lake component licenses

Each component has its own `LICENSE` and `source.json`. The per-component files preserve attribution even where several upstream projects use byte-identical Apache-2.0 license text. No file here is presented as a component-specific NOTICE unless an independent upstream NOTICE was found.

The fixed source trees and file-level copyright headers remain under `/opt/lean-lib/mathlib4/` and its `.lake/packages/` directories. `source.json` gives the public repository, full commit, source archive, fixed license URL, and recursive NOTICE search for every component.

A recursive fixed-commit Git tree search found no independent NOTICE or COPYRIGHT file for these nine components. mathlib and batteries each have only a `.vscode/copyright.code-snippets` editor template; those templates are documented in their `source.json` and are not treated as standalone notices.

| Component | License | Fixed commit | Public source | Installed material |
|---|---|---|---|---|
| mathlib | Apache-2.0 | `5b3f719bf129e3cf48daf6ff76a2ec5cb6e9b1e3` | https://github.com/leanprover-community/mathlib4 | `mathlib/LICENSE`, `mathlib/source.json` |
| plausible | Apache-2.0 | `b1c4a69a7e247ab7df20460212001673d74f08c0` | https://github.com/leanprover-community/plausible | `plausible/LICENSE`, `plausible/source.json` |
| LeanSearchClient | Apache-2.0 | `0498c7c070c143a3bf7379f4d99a2c63bb9d9715` | https://github.com/leanprover-community/LeanSearchClient | `LeanSearchClient/LICENSE`, `LeanSearchClient/source.json` |
| importGraph | Apache-2.0 | `18a90119a5d316358fde6c86e0ca24e59212e32c` | https://github.com/leanprover-community/import-graph | `importGraph/LICENSE`, `importGraph/source.json` |
| proofwidgets | Apache-2.0 | `b1436dc749e722c9920036b52cdc43b3451d0b69` | https://github.com/leanprover-community/ProofWidgets4 | `proofwidgets/LICENSE`, `proofwidgets/source.json` |
| aesop | Apache-2.0 | `57d3325be72a842920813bcb40f96a6f7393c185` | https://github.com/leanprover-community/aesop | `aesop/LICENSE`, `aesop/source.json` |
| Qq | Apache-2.0 | `ee41917ae11d38479fb8fb24745f7ca4bf0a784d` | https://github.com/leanprover-community/quote4 | `Qq/LICENSE`, `Qq/source.json` |
| batteries | Apache-2.0 | `d60e6444e6fd881dfa077ff36e96de75753afa28` | https://github.com/leanprover-community/batteries | `batteries/LICENSE`, `batteries/source.json` |
| Cli | MIT | `da07ca808b6718cb2aed14dba154e5a08b8f8ecf` | https://github.com/leanprover/lean4-cli | `Cli/LICENSE`, `Cli/source.json` |

These are license and source-location materials. They do not assert that every fixed source archive was downloaded or that the full image license review is complete.
