"""Complete Solver runtime recipes without mutating distribution decisions.

Recipes are declarations. They do not claim image or real-judge acceptance.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path



def curriculum_tools_recipe(root: Path, row: dict) -> None:
    """Bind unchanged library bytes to fixed public downloads, preserving history."""
    from .layout import load
    from .resources import content_digest, digest
    recipe = load(root / row['recipe'])
    files = load(root / row['files_manifest'])['files']
    identity = content_digest(files, row['target_root'])
    if identity != row['content_digest'] or digest(root / row['files_manifest']) != row['manifest_sha256']:
        raise ValueError('Curriculum public tool recipe must preserve its frozen file identity')
    recipe_sha = digest(root / row['recipe'])
    changed = row.get('public_tool_recipe_sha256') != recipe_sha or row.get('recipe_format') != 'official_files'
    if changed:
        history = {key:deepcopy(value) for key,value in row.items()
                   if key in {'image_digest','product_prepared','status','source_input','source_input_file'}
                   or key.endswith('_verified')}
        if history and 'previous_tool_acquisition' not in row:
            row['previous_tool_acquisition'] = history
        for key in list(row):
            if key.endswith('_verified') and isinstance(row[key],bool):
                row[key] = False
        row.update(product_prepared=False, runtime_verified=False, status='local_preparation_required')
    row.update(recipe_format='official_files', source_inputs=deepcopy(recipe['sources']),
               public_tool_recipe_sha256=recipe_sha,
               acquisition={'preferred':'local_build'}, distribution='local_prepare',
               public_upload_allowed=False,
               distribution_evidence='docs/licenses/third-party/curriculum-tools-public-source.json')
    row.pop('source_input',None)
    row.pop('source_input_file',None)


def sports_tools_recipe(root: Path, row: dict) -> None:
    """Declare the new source-built validator without inheriting old acceptance."""
    from .layout import load
    from .resources import content_digest, digest
    from .build import build_definition
    recipe_path = 'assets/environments/solver/resources/solver-itc2021-sports-timetabling-development-tools-recipe.json'
    recipe = load(root / recipe_path)
    files = load(root / row['files_manifest'])['files']
    identity = content_digest(files, row['target_root'])
    recipe_sha = digest(root / recipe_path)
    context = 'assets/environments/solver/itc2021-sports-timetabling/tools'
    definition = {'dockerfile': context + '/Dockerfile', 'context': context,
                  'pull_args': {'TCSEXAM_BUILDER_IMAGE': recipe['builder_image']}}
    candidate = deepcopy(row)
    candidate.update(build=definition)
    candidate.pop('recipe', None)
    source = build_definition(root, candidate)['source_digest']
    changed = (row.get('public_tool_recipe_sha256') != recipe_sha
               or row.get('content_digest') != identity or row.get('build') != definition
               or row.get('source_recipe_source_digest') != source)
    if changed:
        row.setdefault('previous_tool_identity', deepcopy(row))
        for key in list(row):
            if key.endswith('_verified') and isinstance(row[key], bool):
                row[key] = False
        row.update(product_prepared=False, runtime_verified=False, status='local_preparation_required')
    row.update(build=definition, dependencies=[], content_digest=identity,
               manifest_sha256=digest(root / row['files_manifest']),
               content_version='official-source-636951ec-ubuntu22-gcc11-v1',
               public_source_recipe=recipe_path, public_tool_recipe_sha256=recipe_sha,
               acquisition={'preferred':'local_build'}, distribution='local_prepare',
               public_upload_allowed=False,
               distribution_evidence='docs/licenses/third-party/sports-tools-public-source.json',
               source_recipe_generator='tcsexam.solver_recipes', source_recipe_status='declared')
    for key in ('recipe', 'recipe_format', 'source_input', 'source_input_file',
                'image_digest', 'image_id', 'image', 'reference', 'public_image', 'replacement'):
        row.pop(key, None)
    row['source_recipe_source_digest'] = source


def solver_runtime_manifest(root: Path, document: dict) -> dict:
    result = deepcopy(document)
    rows = result["images"]
    by_id = {row["id"]: row for row in rows if row.get("id")}
    curriculum_tools_recipe(root, by_id['solver-curriculum-itc2007-development-tools'])
    sports_tools_recipe(root, by_id['solver-itc2021-sports-timetabling-development-tools'])
    qbf_tools = "solver-qbf-qbfeval-development-tools"
    if qbf_tools not in by_id:
        row = {"id":qbf_tools, "type":"toolchain", "distribution":"local_prepare", "public_upload_allowed":False, "consumers":["tasks/solver/online/qbf-qbfeval", "tasks/solver/offline/qbf-qbfeval"], "build":{"dockerfile":"assets/environments/solver/qbf-qbfeval/tools/Dockerfile", "context":"assets/environments/solver/qbf-qbfeval/tools"}, "dependencies":[], "product_prepared":False, "runtime_verified":False, "status":"local_preparation_required", "source_recipe_generator":"tcsexam.solver_recipes"}
        rows.append(row)
        by_id[qbf_tools] = row
    def runtime(task, protocol, role):
        consumer = f"tasks/solver/{protocol}/{task}"
        matches = [r for r in rows if r.get("runtime_role") == role and consumer in r.get("consumers", [])]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one {role} product for {consumer}, found {len(matches)}")
        return matches[0]
    def install(row, definition):
        from .build import build_definition
        previous_build = row.get("build")
        previous_dependencies = row.get("dependencies", [])
        previous_source = row.get("source_recipe_source_digest")
        dependencies = sorted(set(definition.get("image_args", {}).values()))
        row["build"] = definition
        row["dependencies"] = dependencies
        source = build_definition(root, row)["source_digest"]
        changed = (previous_build != definition or previous_dependencies != dependencies
                   or previous_source != source)
        if changed:
            # Keep the old immutable product's evidence separately. A source
            # declaration cannot transfer acceptance to a new environment.
            accepted = {key:deepcopy(value) for key,value in row.items()
                        if key in {"image_digest", "content_digest", "verification_scope"}
                        or key.endswith("_verified")}
            if accepted and "previous_recipe_acceptance" not in row:
                row["previous_recipe_acceptance"] = accepted
            row["runtime_verified"] = False
            row["product_prepared"] = False
            for key in ("startup_verified", "harbor_verified", "content_verified",
                        "permissions_verified", "final_filesystem_isolation_verified",
                        "historical_layer_isolation_verified"):
                if row.get(key) is True:
                    row[key] = False
            row["status"] = "local_preparation_required"
        row["source_recipe_status"] = "declared"
        row["source_recipe_source_digest"] = source
        row["source_recipe_generator"] = "tcsexam.solver_recipes"
    install(by_id[qbf_tools], deepcopy(by_id[qbf_tools]["build"]))
    for directory in sorted((root / "tasks/solver/online").iterdir()):
        if not (directory / "task.toml").is_file():
            continue
        task = directory.name
        public = "bpplib-development" if task == "bpp-bpplib" else "qbf-public" if task == "qbf-qbfeval" else f"solver-{task}-development-data"
        hidden = "bpplib-judging" if task == "bpp-bpplib" else "qbf-judging" if task == "qbf-qbfeval" else f"solver-{task}-judging-data"
        online = runtime(task, "online", "development")
        offline = runtime(task, "offline", "development")
        verifier = runtime(task, "offline", "verifier")
        backend = runtime(task, "online", "backend")
        public_backend = runtime(task, "online", "public_backend")
        definition = deepcopy(online.get("build", {}))
        definition.update(dockerfile=f"tasks/solver/online/{task}/environment/Dockerfile", context=f"tasks/solver/online/{task}/environment")
        if task == "christmas-tree-ahc041":
            # Practice instances come from the declared data product. Local
            # recovery copies do not participate in Docker COPY or its identity.
            environment = f"tasks/solver/online/{task}/environment"
            definition["source_paths"] = [f"{environment}/{path}" for path in (
                "Dockerfile", "submit.sh", "public_runner.py", "app/solver.cpp",
                "app/build.sh", "app/run_public.py", "app/public_reference.json",
                "app/tools",
            )]
        args = {"BPPLIB_DATA_IMAGE" if task == "bpp-bpplib" else "QBF_PUBLIC_DATA_IMAGE" if task == "qbf-qbfeval" else "TCSEXAM_PUBLIC_DATA_IMAGE": public}
        source = (directory / "environment/Dockerfile").read_text()
        for arg in ("TCSEXAM_TOOLS_IMAGE", "QBF_TOOLS_IMAGE"):
            if f"ARG {arg}" in source:
                candidates = [r["id"] for r in rows if r.get("type") == "toolchain" and (f"tasks/solver/online/{task}" in r.get("consumers", []) or (task == "qbf-qbfeval" and r.get("id") == qbf_tools))]
                if len(candidates) != 1:
                    raise ValueError(f"Expected a unique toolchain for {task}: {candidates}")
                args[arg] = candidates[0]
        definition["image_args"] = args
        if "ARG TCSEXAM_PYTHON_IMAGE" in source:
            definition.setdefault("pull_args", {})["TCSEXAM_PYTHON_IMAGE"] = "python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464"
        install(online, definition)
        install(offline, {"dockerfile":f"tasks/solver/offline/{task}/environment/Dockerfile", "context":f"tasks/solver/offline/{task}/environment", "image_args":{"TCSEXAM_OFFLINE_DEVELOPMENT_IMAGE":online["id"]}})
        for row, split, data in ((backend, "hidden", hidden), (public_backend, "public", public)):
            paths = [f"assets/environments/solver/{task}/judge", "assets/environments/solver/judge-runtime", f"tasks/solver/online/{task}/tests", f"tasks/solver/online/{task}/environment/app/public_reference.json", f"tasks/solver/offline/{task}/tests/runtime/task.json"]
            if task == "vc-pace2019" and split == "hidden":
                paths.append("assets/data/solver/solver-vc-pace2019-judging-data-files.json")
            install(row, {"dockerfile":f"assets/environments/solver/{task}/judge/Dockerfile.{split}", "context":".", "source_paths":paths, "image_args":{"TCSEXAM_CLEAN_TOOLS_IMAGE":online["id"], "TCSEXAM_JUDGE_DATA_IMAGE":data}})
        install(verifier, {"dockerfile":f"tasks/solver/offline/{task}/tests/Dockerfile", "context":".", "source_paths":["assets/environments/solver/offline-runtime", f"tasks/solver/offline/{task}/tests"], "image_args":{"TCSEXAM_OFFLINE_BACKEND_IMAGE":backend["id"]}})
        if task in {"ce-pace2021", "dfvs-pace2022", "oscm-pace2024", "vc-pace2019"}:
            base = by_id[f"{task}-backend-base"]
            install(base, {"dockerfile":"assets/environments/solver/judge-runtime/Dockerfile.alias", "context":"assets/environments/solver/judge-runtime", "image_args":{"TCSEXAM_CLEAN_TOOLS_IMAGE":online["id"]}})
    return result


def solver_public_image_map(root: Path, document: dict, references: dict[str, str], *, tasks: set[str] | None = None) -> dict[str, str]:
    """Bind requested judge references to their separately built public images.

    References must be local product IDs or immutable image references already
    accepted by preparation. The service uses this allowlist for ordinary tokens;
    final hidden sessions continue to require the verifier-only credential.
    """
    rows = document["images"]
    result = {}
    for directory in sorted((root / "tasks/solver/online").iterdir()):
        if tasks is not None and directory.name not in tasks:
            continue
        consumer = f"tasks/solver/online/{directory.name}"
        ids = {}
        for role in ("backend", "public_backend"):
            matches = [r["id"] for r in rows if r.get("runtime_role") == role and consumer in r.get("consumers", [])]
            if len(matches) != 1:
                raise ValueError(f"Expected one {role} for {consumer}")
            ids[role] = matches[0]
        missing = [identity for identity in ids.values() if not references.get(identity)]
        if missing:
            raise ValueError(f"Prepared judge image references unavailable: {missing}")
        hidden, public = references[ids["backend"]], references[ids["public_backend"]]
        if hidden == public:
            raise ValueError(f"Public and hidden judging images must be independently composed: {consumer}")
        if hidden in result and result[hidden] != public:
            raise ValueError("A requested judge image maps to multiple public products")
        result[hidden] = public
    return result
