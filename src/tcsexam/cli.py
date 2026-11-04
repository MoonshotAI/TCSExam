"""Select TCSExam tasks, prepare Harbor jobs, and calculate scores."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from .layout import PROTOCOLS, TRACKS, load, repository, require_paths, selection, within
from .scoring import aggregate, relative_score
from .agent_config import add_agent_arguments, configure_agent


def dump(value, path=None):
    data = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
    else:
        print(data, end="")


def resolve(args):
    root = repository(args.root)
    suite, rows = selection(root, args.suite, args.track, args.task, args.solver_protocol)
    if getattr(args, 'data_recipe', None):
        from .fixed_data_archive import recipe_choices, explicit_inputs, effective_resource, check_explicit_input
        from .resources import resource_by_id
        from .setup import cache_path
        choices = recipe_choices(args.data_recipe)
        inputs = explicit_inputs(getattr(args, 'input', None))
        for identity in choices:
            resource = effective_resource(root, resource_by_id(root, identity), choices)
            check_explicit_input(root, resource, cache_path(args) / 'downloads', inputs)
    if args.solver_protocol is None:
        args.solver_protocol = suite.get("default_solver_protocol", "offline")
    if (getattr(args, 'command', None) in {'setup', 'prepare', 'doctor', 'run', 'backend'}
            and not getattr(args, 'artifacts', None)):
        from .build import selection_artifact_path
        candidate = selection_artifact_path(root, rows, args)
        if candidate.is_file():
            args.artifacts = candidate
    if getattr(args, 'data_recipe', None) and getattr(args, 'artifacts', None):
        # Explicit route requests must never silently consume a different saved
        # route, even when the requested archive has already been checked.
        from .build import validate_manifest
        document = load(args.artifacts)
        validate_manifest(root, document)
        records = {row.get('id'): row for row in document.get('images', [])}
        for identity, option in choices.items():
            current = effective_resource(root, resource_by_id(root, identity), choices)
            record = records.get(identity, {})
            if (record.get('selected_data_recipe') != option
                    or record.get('data_recipe_signature') != current['data_recipe_signature']):
                raise ValueError('Artifact manifest does not match the requested data recipe: ' + identity)
    return root, rows


def prepare(args):
    root, rows = resolve(args)
    require_paths(rows)
    settings = configure_agent(args)
    if args.concurrency < 1 or args.attempts < 1:
        raise ValueError("Concurrency and attempts must be positive")
    from .backend_cli import client_plan
    backend_plan = client_plan(root, rows, args)
    concurrency = min(args.concurrency, backend_plan['scheduling']['max_concurrent_trials']) if backend_plan else args.concurrency
    suffix = args.solver_protocol if any(r["track"] == "solver" for r in rows) else "shared"
    selected = args.track or ('-'.join(args.task) if isinstance(args.task, list) else args.task) or 'all'
    config = {
        "job_name": f"tcsexam-{args.suite}-{suffix}-{selected}-{uuid4().hex[:12]}",
        "jobs_dir": str(root / "jobs"), "n_attempts": 1,
        "n_concurrent_trials": concurrency, "timeout_multiplier": 1.0,
        "retry": {"max_retries": 0}, "environment": {"type": "docker"},
        "agents": [settings.config],
        "tasks": [],
        "artifacts": ["/app"]}
    from .runtime import materialize
    config['tasks'], attempts = materialize(root, rows, args)
    from harbor.models.job.config import JobConfig
    JobConfig.model_validate(config)
    try:
        commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                         stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"],
                                            text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    metadata = {"suite": args.suite, "solver_protocol": suffix if suffix != "shared" else None,
                "repository_commit": commit, "uncommitted_changes": dirty,
                **settings.provenance, "attempts": args.attempts,
                "requested_concurrency": args.concurrency, "effective_concurrency": concurrency,
                "backend_scheduling": backend_plan['scheduling'] if backend_plan else None,
                "tasks": rows, "runtime_attempts": attempts}
    dump(config, args.output)
    provenance = args.output.with_suffix(".selection.json")
    dump(metadata, provenance)
    print(f"Wrote {len(rows)} tasks ({suffix}) to {args.output}; selection record: {provenance}")
    return config


def doctor(args):
    root, rows = resolve(args)
    from .diagnostics import prerequisites
    report = {"suite": args.suite, "solver_protocol": args.solver_protocol,
              **prerequisites(root, rows, args)}
    dump(report, args.output)
    return 0 if report["ready"] else 2


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("list", "build", "setup", "prepare", "doctor", "run"):
        q = sub.add_parser(name)
        q.add_argument("--root", type=Path, help="TCSExam source checkout")
        q.add_argument("--suite", choices=["lite", "full"], default="lite")
        q.add_argument("--track", choices=TRACKS)
        q.add_argument("--task", action="append", help="Task ID; repeat or use a comma-separated list")
        q.add_argument("--solver-protocol", choices=PROTOCOLS,
                       help="Override the suite default (Full: online; Lite: offline)")
        if name != "list":
            q.add_argument("--output", type=Path,
                           default=Path("build/k3-job.json") if name in {"prepare", "run"} else None,
                           help="Job configuration, report, or build manifest output")
            q.add_argument("--image-map", type=Path, help="Task-path to pinned development/verifier images")
            q.add_argument("--artifacts", type=Path, help="Optional external image product manifest")
            q.add_argument("--docker-context", help="Docker context of the actual execution host")
            q.add_argument("--cache", type=Path, help="Verified resource cache (default TCSEXAM_CACHE)")
            q.add_argument("--judge-url", help="User's TCSEXAM backend base URL")
            q.add_argument("--backend-plan", type=Path, help="Resource plan produced by backend configure")
        if name in {"build", "setup", "run"}:
            q.add_argument('--data-recipe', action='append', default=[], metavar='PRODUCT=fixed_archive',
                           help='Explicitly select one declared fixed input archive recipe')
            q.add_argument('--input', action='append', default=[], metavar='NAME=PATH',
                           help='Declared local source input; may be repeated')
            q.add_argument("--pull-policy", choices=["missing", "always", "never"], default="missing")
        if name == "run":
            q.add_argument("--yes", "-y", action="store_true",
                           help="Explicitly approve Harbor loading the declared host environment variables")
        if name in {"prepare", "run", "doctor"}:
            add_agent_arguments(q)
        if name in {"prepare", "run"}:
            q.add_argument("--concurrency", type=int, default=1)
            q.add_argument("--attempts", type=int, default=1)
    q = sub.add_parser("source-inputs", help="Prepare fixed public Lean source archives before local builds")
    q.add_argument("--root", type=Path)
    q.add_argument("--cache", type=Path)
    q.add_argument("--input", action="append", default=[], metavar="graphviz=PATH|wrapper=PATH",
                   help="Import an exact declared archive instead of downloading it")
    q.add_argument("--offline", action="store_true", help="Use verified context, cache or explicit inputs only")
    q = sub.add_parser("resources", help="Prepare declared source inputs for a data-image rebuild")
    q.add_argument("--root", type=Path)
    q.add_argument("--resource", "--bundle", dest="resource", required=True)
    q.add_argument("--cache", type=Path, default=Path(os.environ.get("TCSEXAM_CACHE", "").strip() or "~/.cache/tcsexam"))
    q.add_argument("--archive", type=Path, help="Checked local public archive while its URL is pending")
    q.add_argument('--data-recipe', action='append', default=[], metavar='PRODUCT=fixed_archive',
                   help='Explicitly select one declared fixed input archive recipe')
    q.add_argument("--input", action="append", default=[], metavar="NAME=PATH",
                   help="Declared local source input; may be repeated")
    q.add_argument("--image", help="Build and push a data image to this explicitly authorized target")
    q.add_argument("--registry", help="Authorized registry repository prefix for --image")
    q.add_argument("--builder", choices=["remote", "remote-acr"], default="remote")
    q.add_argument("--docker-context", help="Docker context used to compile official tools")
    q.add_argument("--pull-policy", choices=["missing", "always", "never"], default="missing")
    q.add_argument("--context", type=Path, help="New persistent data build-context directory")
    q.add_argument("--metadata-file", type=Path, help="BuildKit image-digest output file")
    q.add_argument("--public", action="store_true",
                   help="Authorize public distribution; the resource must explicitly permit it")
    q = sub.add_parser("backend", help="Run or check the online judging backend service")
    q.add_argument("action", choices=["configure", "serve", "check"])
    q.add_argument("--config", type=Path, default=Path('build/backend.yaml'), help="Backend YAML config")
    q.add_argument("--host", help="Override config host (serve)")
    q.add_argument("--port", type=int, help="Override config port (serve)")
    q.add_argument("--root", type=Path)
    q.add_argument("--suite", choices=['full', 'lite'], default='full')
    q.add_argument("--track", choices=TRACKS, default='solver')
    q.add_argument("--task", action='append')
    q.add_argument("--solver-protocol", choices=PROTOCOLS, default='online')
    q.add_argument("--artifacts", type=Path)
    q.add_argument("--cache", type=Path)
    q.add_argument("--docker-context")
    q.add_argument("--judge-url", help="Backend origin reachable from development and worker containers")
    q.add_argument("--state-dir", type=Path, default=Path('build/backend-state'))
    q.add_argument("--storage-limit", default='standard', help="standard, a MiB limit, or explicit none")
    q = sub.add_parser("score")
    q.add_argument("--root", type=Path)
    q.add_argument("--attempts", type=Path, required=True)
    q.add_argument("--suite", choices=["lite", "full"], required=True)
    q.add_argument("--cohort", type=Path, required=True)
    q.add_argument("--output", type=Path)
    q = sub.add_parser("solver-score")
    q.add_argument("--task", required=True)
    q.add_argument("--records", type=Path, required=True)
    q.add_argument("--reference", default="full", help="full, lite, or a reference JSON file")
    q.add_argument("--output", type=Path)
    q = sub.add_parser("export", help="Export a constrained source tree without Git history or private inputs")
    q.add_argument("--root", type=Path)
    q.add_argument("--output", type=Path, required=True)
    q.add_argument("--normalize-modes", action="store_true",
                   help="Use 0755 directories and 0644/0755 files, retaining executable status")
    for command in ("validate", "check-public"):
        q = sub.add_parser(command)
        q.add_argument("--root", type=Path)
        q.add_argument("--output", type=Path)
        if command == "check-public":
            q.add_argument("--phase", choices=["source", "release"], default="release")
    args = p.parse_args(argv)
    try:
        if args.command == "list":
            _, rows = resolve(args)
            for r in rows:
                print(f"{r['track']:14} {r['id']:38} {r['path'] or '(offline adapter pending)'}")
        elif args.command == "source-inputs":
            from .source_inputs import explicit_sources, prepare_source_inputs
            from .setup import cache_path
            dump(prepare_source_inputs(repository(args.root), cache_path(args),
                                       explicit_sources(args.input), args.offline))
        elif args.command == "prepare":
            prepare(args)
        elif args.command == "build":
            from .build import build_selection
            root, rows = resolve(args)
            dump(build_selection(root, rows, args))
        elif args.command == "setup":
            from .setup import setup_selection
            root, rows = resolve(args)
            dump(setup_selection(root, rows, args), args.output)
        elif args.command == "run":
            settings = configure_agent(args)
            settings.require_credentials()
            root, rows = resolve(args)
            require_paths(rows)
            # All image acquisition precedes the agent and its development budget.
            from .setup import setup_selection
            preparation = setup_selection(root, rows, args)
            from argparse import Namespace
            report = args.output.with_suffix(".readiness.json")
            if doctor(Namespace(**{**vars(args), "output": report})):
                raise ValueError(f"Run prerequisites remain; see {report}")
            config = prepare(args)
            print(f"Starting {args.suite}: {len(config['tasks'])} tasks; Solver {args.solver_protocol}", flush=True)
            host_env = {**os.environ, **settings.host_overrides}
            from .setup import cache_path
            host_env['TCSEXAM_CACHE'] = str(cache_path(args))
            if args.docker_context:
                host_env['DOCKER_CONTEXT'] = args.docker_context
            probe = next((row.get('local_image') or row.get('image')
                          for row in preparation.get('host_support', [])
                          if row.get('support_kind') == 'harbor_kernel_probe'), None)
            if probe:
                host_env['TCSEXAM_HARBOR_KERNEL_PROBE_IMAGE'] = probe
            command = [sys.executable, "-m", "tcsexam.harbor_launch", "run",
                       "--config", str(args.output.resolve())]
            if args.yes:
                command.append("--yes")
            return subprocess.call(command, env=host_env)
        elif args.command == "doctor":
            return doctor(args)
        elif args.command == "resources":
            from .resources import build_data_image, prepare_resource
            from .fixed_data_archive import explicit_inputs, recipe_choices
            inputs = explicit_inputs(args.input)
            choices = recipe_choices(args.data_recipe)
            if set(choices) - {args.resource}:
                raise ValueError('The selected data recipe must match --resource')
            if args.archive:
                inputs['frozen_input'] = args.archive
            if args.image:
                if not args.registry or not args.context or not args.metadata_file:
                    raise ValueError('--image requires --registry, --context and --metadata-file')
                dump(build_data_image(repository(args.root), args.resource, args.cache,
                    args.image, args.builder, inputs, args.context, args.metadata_file,
                    registry_prefix=args.registry, public=args.public, args=args))
            else:
                print(prepare_resource(repository(args.root), args.resource, args.cache, inputs,
                                       args=args))
        elif args.command == "backend":
            if args.action == 'configure':
                from .backend_cli import configure
                root, rows = resolve(args)
                dump(configure(root, rows, args))
                return 0
            try:
                from aiohttp import web
                from .backend.adapter import load_adapter
                from .backend.config import load_config
                from .backend.server import create_app
            except ImportError as e:
                p.exit(2, f"Error: install the backend dependencies with pip install -e '.[backend]': {e}\n")
            config = load_config(args.config)
            if args.host:
                config.host = args.host
            if args.port:
                config.port = args.port
            if args.action == "check":
                sessions_cfg = config.backend.judge_sessions
                summary = {
                    "service_name": config.service_name,
                    "listen": f"{config.host}:{config.port}",
                    "public_url": config.public_url(),
                    "auth_enabled": config.auth_enabled,
                    "run_id_mode": config.run_id_mode,
                    "state_dir": str(config.state_dir),
                    "archive_token_configured": bool(config.archive_token),
                    "adapter": config.adapter or None,
                    "worker_group": config.worker_group,
                    "judge_sessions": {
                        "max_sessions": sessions_cfg.max_sessions,
                        "profile": sessions_cfg.profile,
                        "spec": sessions_cfg.spec,
                        "work_dir": sessions_cfg.work_dir,
                        "command": sessions_cfg.command,
                        "judge_port": sessions_cfg.judge_port,
                        "ready_timeout_seconds": sessions_cfg.ready_timeout_seconds,
                        "ttl_seconds": sessions_cfg.ttl_seconds,
                        "max_ttl_seconds": sessions_cfg.max_ttl_seconds,
                        "read_timeout_seconds": sessions_cfg.read_timeout_seconds,
                        "idle_ttl_seconds": sessions_cfg.idle_ttl_seconds,
                        "max_shards": sessions_cfg.max_shards,
                        "min_ready_ratio": sessions_cfg.min_ready_ratio,
                        "hibernate_enabled": sessions_cfg.hibernate_enabled,
                        "submission_cap_enabled": sessions_cfg.submission_cap.enabled,
                    },
                    "backend": {
                        "create_retries": config.backend.create_retries,
                        "create_concurrency": config.backend.create_concurrency,
                        "session_create_concurrency": config.backend.session_create_concurrency,
                        "max_sandboxes_global": config.backend.max_sandboxes_global,
                        "max_sandbox_memory_mb": config.backend.max_sandbox_memory_mb,
                        "ready_timeout_seconds": config.backend.ready_timeout_seconds,
                    },
                }
                adapter = load_adapter(config.adapter, config)
                summary["adapter_loaded"] = type(adapter).__name__
                dump(summary)
                return 0
            config.state_dir.mkdir(parents=True, exist_ok=True)
            web.run_app(create_app(config), host=config.host, port=config.port,
                        print=lambda msg: print(msg, flush=True))
        elif args.command == "score":
            root = repository(args.root)
            cohort = load(args.cohort)
            if cohort.get("solver_protocol") not in PROTOCOLS:
                raise ValueError("Declare solver_protocol: online or offline in the cohort")
            with args.attempts.open(newline="") as f:
                result = aggregate(list(csv.DictReader(f)), load(root / f"suites/{args.suite}.json"), cohort)
            dump(result, args.output)
        elif args.command == "solver-score":
            if args.reference in {"full", "lite"}:
                from importlib.resources import files
                reference = json.loads(files("tcsexam").joinpath(
                    f"references/paper-k3-fixed-260925-{args.reference}.json").read_text())
            else:
                reference = load(args.reference)
            dump(relative_score(args.task, load(args.records), reference), args.output)
        elif args.command == "export":
            from .export import export_source
            dump(export_source(repository(args.root), args.output, args.normalize_modes))
        elif args.command == "validate":
            from .checks import validate
            dump(validate(repository(args.root)), args.output)
        elif args.command == "check-public":
            from .checks import publication
            result = publication(repository(args.root), phase=args.phase)
            dump(result, args.output)
            return 0 if result["ready_for_publication"] else 2
    except ImportError as e:
        p.exit(2, f"Error: install the runtime dependencies with pip install -e '.[runtime]': {e}\n")
    except (ValueError, KeyError, OSError, AssertionError, subprocess.SubprocessError) as e:
        p.exit(2, f"Error: {e}\n")
    return 0
