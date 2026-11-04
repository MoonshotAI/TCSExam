#!/usr/bin/env python3
"""Schema and loading validation for per-problem metric configuration.

One configuration per problem (a JSON file tracked in git under the task package’s tests/ directory):
{
  "shape": "gap_ratio",          // shape name; must exist in the engine shape library
  "anchors_file": "anchors.json", // anchor data file, relative to the configuration file directory
  "direction": "max",            // optimization direction: "max" or "min"
  "params": {}                   // shape-specific parameters (including reserved parameters for scaffold shapes)
}

Anchor data file format (JSON):
{"K": {"<instance_name>": <best_known_score>, ...}, "B": {"<instance_name>": <factory_baseline_score>, ...}}
For decision problems (solve_rate / certificate_adjust), anchor values use 1/0 for solved/unsolved.
"""
import json
import os

from engine import SHAPES, MetricConfigError, load_anchors

REQUIRED_FIELDS = ("shape", "anchors_file", "direction")
DIRECTIONS = ("max", "min")


def validate_config(data):
    """Validate a configuration dict and return the normalized configuration."""
    if not isinstance(data, dict):
        raise MetricConfigError("Configuration must be a JSON object")
    for field in REQUIRED_FIELDS:
        if field not in data:
            raise MetricConfigError(f"Configuration is missing required field: {field}")
    if data["shape"] not in SHAPES:
        raise MetricConfigError(
            f"Unknown shape {data['shape']!r}; available: {sorted(SHAPES)}"
        )
    if data["direction"] not in DIRECTIONS:
        raise MetricConfigError(f"direction must be one of {DIRECTIONS}; got {data['direction']!r}")
    if not isinstance(data["anchors_file"], str) or not data["anchors_file"]:
        raise MetricConfigError("anchors_file must be a non-empty string (a path relative to the configuration file)")
    params = data.get("params", {})
    if not isinstance(params, dict):
        raise MetricConfigError("params must be a JSON object")
    return {
        "shape": data["shape"],
        "anchors_file": data["anchors_file"],
        "direction": data["direction"],
        "params": params,
    }


def load_config(path):
    """Read and validate configuration from a JSON file; resolve anchors_file to an absolute path."""
    with open(path) as f:
        data = json.load(f)
    config = validate_config(data)
    if not os.path.isabs(config["anchors_file"]):
        config["anchors_file"] = os.path.join(os.path.dirname(os.path.abspath(path)),
                                              config["anchors_file"])
    return config


def load_task(config_path):
    """Load everything at once: read the configuration and anchor data, then return (config, anchors)."""
    config = load_config(config_path)
    anchors = load_anchors(config["anchors_file"])
    return config, anchors
