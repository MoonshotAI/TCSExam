# Prepare public self-test images

[English](public-images.md) | [简体中文](public-images.zh-CN.md)

This guide builds a public self-test image from an existing judge image.
It is for operators configuring the Online backend's public-session image map.

Public self-test images contain public inputs, reference values, tools and approved
practice files. Keep hidden inputs, hidden references, credentials and unapproved
answers out of every retained layer. The manifest records which files belong in
the public image. Review it before building.

## Manifest

A schema-version-1 manifest has this shape:

```json
{
  "schema_version": 1,
  "task": "tasks/solver/online/example-task",
  "remove_paths": ["/tests"],
  "allow_content_paths": [
    "/tests-public",
    "/public-instances",
    "/public_reference.json",
    "/judge"
  ],
  "required_paths": [
    "/judge/entry.sh",
    "/tests-public/checker.py",
    "/tests-public/reference.json",
    "/tests-public/instances",
    "/public-instances"
  ],
  "distribution": "redistributable",
  "public_upload_allowed": true
}
```

`distribution` and `public_upload_allowed` control registry writes. A public
`--push` requires `redistributable` and `public_upload_allowed: true`; missing
or unresolved decisions are rejected. For an explicitly authorized private
registry, add `--private-registry`. `local_prepare` and `private_only` products
may use only that route. Local builds and runs use the declared preparation route.

Paths must be absolute and canonical. `/`, relative paths, `.` components, and
`..` components are rejected. `remove_paths` controls what leaves the image and
must cover `/tests/anchors.json`, `/tests/reference-hidden.json`, and
`/tests/solution` (directly or through a parent such as `/tests`), even when a
particular image does not contain them. `allow_content_paths` is only an
explicit statement that matching file contents are public and may be duplicated;
use `payload_allowlist` to restrict the files retained under a sensitive root.
The SHA256 check detects exact regular-file copies. Review the selected files
also for transformed hidden inputs and embedded credentials.

A manifest that needs path-level isolation adds `payload_allowlist`. Each entry
covers one non-overlapping sensitive root and repeats its expected file count as
an independent consistency check:

```json
"payload_allowlist": [
  {
    "root": "/app",
    "files": ["/app/public.txt", "/app/solutions/public-example.sol"],
    "regular_file_count": 2
  }
]
```

Every listed file must be below the root, the declared count must equal the
number of unique listed paths, and a payload root must not overlap any removal
root. Directories may occur without being listed. Every other entry below the
root must be an explicitly listed regular file; links, devices, unlisted files,
additional answers, and duplicate regular-file entries fail closed. The same
exact path set and count are required after import. Derive this list from the
current public development environment, public data manifests, and individually
reviewed public practice answers. Do not derive it by listing hidden images, and
keep hidden paths and hashes outside the public manifest.

The DS example is
`assets/environments/solver/ds-pace2025/public-image.json`. It removes the
hidden `/tests` tree while retaining the public checker, reference data,
instances, and judge entrypoint. The source and output image references are CLI
arguments and deliberately do not appear in the manifest.

## Build and verify

On the Docker host holding the source image, run from the repository root:

```bash
PYTHONPATH=src python -m tcsexam.public_image \
  --source-image registry.example/team/ds-judge:hidden \
  --output-image registry.example/team/ds-judge:public \
  --manifest assets/environments/solver/ds-pace2025/public-image.json
```

Replace both image references with your source and destination. Add `--pull` to
fetch the source first. The tool builds a single-layer image and checks its
contents and configuration, then prints a JSON report. Review the report before
using the output tag. If verification fails, inspect the reported paths and fix
the manifest or inputs; a local output tag may remain from the failed attempt.

For image distribution, follow the [component conditions](../licenses/distribution.md).
After reviewing the report and distribution settings, add `--push` to publish
the output. The tool verifies the image before pushing it. Registry credentials
belong in Docker's local configuration.

## Relationship to `public_image_map`

Map the client-requested original judge reference to the verified public image:

```yaml
public_image_map:
  registry.example/team/ds-judge:hidden: registry.example/team/ds-judge:public
```

A public session uses the mapped image with `INSTANCE_SET=public`. Unmapped
references receive HTTP 403. Add this mapping to the backend configuration and
follow the [Docker deployment guide](docker.md).

## Verify before enabling public sessions

On the deployment host, exercise a public submission and check that the response
contains all requested public instance records. Compare the public runner with
the task checker on the same inputs. Check worker resources, verifier-only archive
access and cleanup of the created workers. Keep judging failures separate from
completed scores when inspecting the result.

If distributing a registry image, also check anonymous pull access at its published
address. For adapter creation and cleanup checks, use the
[Docker contract suite](docker.md#adapter-development-and-manual-configuration).

## Image construction and content checks

`tcsexam.public_image` exports the current container rootfs, filters the tar
stream, and creates the output with `docker import`. Flattening the filtered
filesystem removes hidden bytes from the output layers; a Dockerfile deletion
would leave them in earlier layers. The
filtered tar is streamed through an unnamed temporary file rather than loaded
into memory. The resulting image must have exactly one RootFS layer.

The builder preserves `Entrypoint`, `Cmd`, `WorkingDir`, `User`, `ExposedPorts`,
`Volumes`, and `StopSignal`. It discards existing labels and adds neutral
TCSExam labels. Environment entries whose names contain `KEY`, `TOKEN`,
`SECRET`, or `PASSWORD`, case-insensitively, are removed; only their names are
reported. `INSTANCE_SET=public` is set in the output.

The manifest declares paths to remove, paths whose regular-file contents are
explicitly public, paths that must survive, and optionally exact public payload
allowlists for sensitive roots. During the initial streaming scan, the builder
hashes regular files under both the removed and allowed public trees. After
import, it creates a fresh container from the output and re-exports its rootfs.
That independent scan rejects:

* removed paths, `.key` files, and encrypted `.enc` files, including legacy
  `.xz.enc` names;
* known hidden reference and oracle content, even if omitted from the manifest:
  `/tests/anchors.json`, `/tests/reference-hidden.json`, `/tests/solution`, and
  `/tests/reference.json.bak*` backups;
* missing required paths and links resolving into a removed hidden tree;
* any regular file whose SHA256 belongs exclusively to removed content, even
  when that content was copied to an unrelated path;
* for every configured payload root, any non-directory entry that is not one of
  the exact listed regular files, plus missing or duplicate listed files and a
  regular-file count mismatch.

Content that also occurs under an allowed public path is excluded from the
hidden-only hash set, so an explicitly public duplicate is accepted. Hash
findings report paths, hashes, and counts, never file contents. All validation,
including the single-layer check and OCI configuration comparison, finishes
before an optional push.
