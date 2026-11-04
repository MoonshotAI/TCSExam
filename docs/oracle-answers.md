# Reference-answer archives

[English](oracle-answers.md) | [简体中文](oracle-answers.zh-CN.md)

This guide explains how to package and verify separately supplied reference answers.
It is for operators who already hold the answers and their source specification.

Reference-answer archives support operator checks with separately supplied
answers. Keep them and their input specifications outside the public checkout
or under the excluded `build/` directory, separate from model development
environments. An archive should contain only its declared answers and metadata.
For ordinary model evaluation, follow the [getting-started guide](getting-started.md).

## Create and verify

`tcsexam.oracle_package` creates a deterministic tar archive with task/variant
coverage, Git origins, per-file hashes, `SHA256SUMS` and a scope statement. Its
own SHA-256 is written to an adjacent `.sha256` file.

```bash
python -m tcsexam.oracle_package create \
  --spec /path/to/answer-specification.json \
  --output /path/to/answer-archives/answers-VERSION.tar.gz \
  --report /path/to/answer-archives/create-report.json

python -m tcsexam.oracle_package verify \
  --package /path/to/answer-archives/answers-VERSION.tar.gz \
  --destination /path/to/new-verification-directory \
  --authority-spec /path/to/answer-specification.json
```

Verification uses a new directory, accepts only regular files, and rejects
missing, additional or out-of-scope content. It checks hashes and manifest
totals and can recheck the authoritative Git blobs. To check whether an answer
is accepted, execute it through the corresponding task verifier separately.

## Publish an authorized archive

Check the rights to every included answer before distribution. Configure your
Buildx builder and registry credentials, then supply an explicit repository and
version tag:

```bash
python -m tcsexam.oracle_package publish \
  --package /path/to/answer-archives/answers-VERSION.tar.gz \
  --destination registry.example.org/namespace/tcsexam-answers:VERSION \
  --confirm-public-release PUBLISH_ORACLE_ANSWERS
```

The command verifies the archive and publishes an OCI data image containing it
and its SHA-256. A missing confirmation, missing destination or `latest` tag is
rejected before publication. Preserve the applicable source notices and
distribution conditions when publishing.
