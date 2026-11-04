"""Run the original checker with task-specific CPU and budget metadata."""
import json
import os
from pathlib import Path
import runpy
import sys
from prepare import prepare

config = json.loads(Path("/judge/task.json").read_text())
public = os.environ.get("INSTANCE_SET", "hidden") == "public"
directory = "/tests-public" if public else "/tests"
instances = directory + "/instances"
prepare(instances)
# Every public backend was composed with public data only. Hidden backends
# retain the same trusted checker and scoring bytes with the other split.
os.environ.update(config.get("judge_env", {}))
os.environ.update(INSTANCES_DIR=instances, JUDGE_JOBS="1")
if not config["pool"]:
    os.environ.setdefault("PER_INSTANCE_SECONDS", str(config["seconds"]))
    os.environ.setdefault("PER_INSTANCE_BUDGET", str(config["seconds"]))
os.environ.setdefault("BUILD_TIMEOUT", str(config["build_seconds"]))
from execution import install
install(config)
sys.path[:0] = [directory, config["module_dir"]]
sys.argv = [directory + "/checker.py"]
runpy.run_path(sys.argv[0], run_name="__main__")
