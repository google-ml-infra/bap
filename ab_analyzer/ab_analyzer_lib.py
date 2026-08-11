# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Library for analyzing A/B benchmark results."""

import json
from pathlib import Path
from typing import TypeAlias
from collections.abc import Mapping
from google.protobuf import json_format
from bap_proto import benchmark_job_pb2
from bap_proto import benchmark_result_pb2
from bap_proto.common import metric_pb2
from utils import markdown_formatter

# Maps A/B group to benchmark result.
AbGroupResultMap: TypeAlias = Mapping[
  benchmark_job_pb2.AbTestGroup, benchmark_result_pb2.BenchmarkResult
]

# Maps config_id to a set of A/B groups.
ResultMapping: TypeAlias = Mapping[str, AbGroupResultMap]


def load_results(results_dir: Path) -> ResultMapping:
  """Scans the results directory and deserializes benchmark result artifacts into protos.

  Expected directory naming convention (files are always named benchmark_result.json):
      shard-benchmark-result-{CONFIG_ID}-{MODE}-{JOB_ID}

  Parsing Logic:
      1. Scans for files named exactly "benchmark_result.json".
      2. Identifies the mode ("BASELINE" or "EXPERIMENT") by finding the last occurrence
         of the keyword in the parent directory's name.
      3. Extracts the Config ID from the parent directory's name by stripping the prefix
         and the mode suffix.

  Args:
      results_dir: The directory path containing downloaded benchmark artifacts.

  Returns:
      A mapping where keys are configuration IDs and values are dictionaries mapping
      the A/B mode (BASELINE or EXPERIMENT) to the deserialized BenchmarkResult proto.

  Raises:
      ValueError: If a result file contains invalid JSON or cannot be parsed into
          the expected protobuf format.
  """
  results = {}

  for path in results_dir.rglob("benchmark_result.json"):
    dir_name = path.parent.name
    base_idx = dir_name.rfind("-BASELINE-")
    exp_idx = dir_name.rfind("-EXPERIMENT-")

    if base_idx == -1 and exp_idx == -1:
      continue

    if base_idx > exp_idx:
      mode = benchmark_job_pb2.AbTestGroup.BASELINE
      head = dir_name[:base_idx]
    else:
      mode = benchmark_job_pb2.AbTestGroup.EXPERIMENT
      head = dir_name[:exp_idx]

    prefix = "shard-benchmark-result-"
    config_id = head[len(prefix) :]

    if config_id not in results:
      results[config_id] = {}

    try:
      with open(path, "r") as f:
        json_data = json.load(f)

      result_proto = benchmark_result_pb2.BenchmarkResult()
      json_format.ParseDict(json_data, result_proto, ignore_unknown_fields=True)
      results[config_id][mode] = result_proto

    except json.JSONDecodeError as e:
      raise ValueError(f"Error decoding JSON for {path}: {e}") from e
    except json_format.ParseError as e:
      raise ValueError(f"Error parsing proto for {path}: {e}") from e

  return results


def _get_comparison_config(
  matrix_map: Mapping[str, benchmark_job_pb2.BenchmarkJob],
  config_id: str,
  metric_name: str,
  stat: metric_pb2.Stat,
) -> tuple[float, metric_pb2.ImprovementDirection]:
  """Retrieves the comparison threshold and improvement direction for a specific metric.

  Args:
      matrix_map: A mapping of configuration IDs to BenchmarkJob definitions.
      config_id: The unique identifier for the benchmark configuration.
      metric_name: The name of the metric to look up (e.g., 'latency').
      stat: The specific statistic (e.g., MEDIAN, P99) to look up.

  Returns:
      A tuple containing:
      - threshold (float): The allowed regression threshold (e.g., 0.05 for 5%).
      - direction (ImprovementDirection): The direction that indicates improvement.
  """
  default_threshold = 0.05
  default_direction = metric_pb2.ImprovementDirection.LESS

  job = matrix_map.get(config_id)
  if not job:
    return default_threshold, default_direction

  metric_spec = next((m for m in job.metrics if m.name == metric_name), None)
  if not metric_spec:
    return default_threshold, default_direction

  stat_spec = next((s for s in metric_spec.stats if s.stat == stat), None)
  if not stat_spec or not stat_spec.HasField("comparison"):
    return default_threshold, default_direction

  comp = stat_spec.comparison
  threshold = comp.threshold.value if comp.HasField("threshold") else default_threshold
  direction = (
    comp.improvement_direction
    if comp.improvement_direction
    != metric_pb2.ImprovementDirection.IMPROVEMENT_DIRECTION_UNSPECIFIED
    else default_direction
  )
  return threshold, direction


def _is_ab_regression(
  base_val: float | None,
  exp_val: float | None,
  threshold: float,
  direction: metric_pb2.ImprovementDirection,
) -> bool:
  """Evaluates whether an A/B metric comparison represents a regression.

  Args:
      base_val: Baseline metric statistic value, or None if missing.
      exp_val: Experiment metric statistic value, or None if missing.
      threshold: Allowed percentage regression threshold (e.g. 0.05).
      direction: Direction indicating metric improvement (LESS or GREATER).

  Returns:
      True if the experiment result regressed relative to baseline, False otherwise.
  """
  if exp_val is None:
    return True
  if base_val is None or base_val == 0:
    return False

  delta = (exp_val - base_val) / base_val
  return (
    delta > threshold
    if direction == metric_pb2.ImprovementDirection.LESS
    else delta < -threshold
  )


def _format_ab_metric_row(
  metric_name: str,
  stat: metric_pb2.Stat,
  base_val: float | None,
  exp_val: float | None,
  threshold: float,
  direction: metric_pb2.ImprovementDirection,
  is_reg: bool,
  unit: str = "",
) -> list[str]:
  """Formats a single A/B metric comparison row.

  Args:
      metric_name: Name of the metric (e.g., 'wall_time').
      stat: The evaluated statistic enum.
      base_val: Baseline statistic value.
      exp_val: Experiment statistic value.
      threshold: Regression threshold.
      direction: Improvement direction.
      is_reg: Boolean indicating if metric comparison is a regression.
      unit: Optional unit string (e.g. 'ms', 's').

  Returns:
      A list of formatted cell strings for the Markdown table row.
  """
  name = markdown_formatter.format_with_subtext(metric_name, metric_pb2.Stat.Name(stat))
  th_str = markdown_formatter.format_percent(threshold)

  if exp_val is None:
    return [
      name,
      markdown_formatter.format_float(base_val, unit=unit),
      "-",
      "N/A",
      th_str,
      markdown_formatter.format_status(None, missing_exp=True),
    ]
  if base_val is None:
    return [
      name,
      "-",
      markdown_formatter.format_float(exp_val, unit=unit),
      "N/A",
      th_str,
      markdown_formatter.format_status(None, missing_base=True),
    ]
  if base_val == 0:
    return [
      name,
      f"0 {unit}".strip(),
      markdown_formatter.format_float(exp_val, unit=unit),
      "0.00%" if exp_val == 0 else "∞",
      th_str,
      markdown_formatter.format_status(
        False if exp_val == 0 else None, undetermined=(exp_val != 0)
      ),
    ]

  delta = (exp_val - base_val) / base_val
  return [
    name,
    markdown_formatter.format_float(base_val, unit=unit),
    markdown_formatter.format_float(exp_val, unit=unit),
    markdown_formatter.format_percent(delta, precision=2, signed=True),
    th_str,
    markdown_formatter.format_status(is_reg),
  ]


def generate_report(
  results: ResultMapping,
  matrix_map: Mapping[str, benchmark_job_pb2.BenchmarkJob],
  repo_url: str,
  workflow_name: str,
) -> tuple[str, bool]:
  """Generates a Markdown report string and a success status.

  Args:
      results: A mapping of configuration IDs to A/B groups (baseline/experiment).
      matrix_map: A mapping of configuration IDs to BenchmarkJob definitions, used to
        retrieve threshold and comparison settings.
      repo_url: The base URL of the repository, used to generate commit links.
      workflow_name: The name of the workflow to display in the report header.

  Returns:
      A tuple containing:
      - report_content (str): The full Markdown report string.
      - success (bool): True if no regressions or failures were detected, False otherwise.

  Raises:
      ValueError: If the results mapping is empty.
  """
  if not results:
    raise ValueError("No A/B benchmark results found.")

  sections = [
    markdown_formatter.format_header(f"A/B Benchmark Results: {workflow_name}", level=1)
  ]
  global_success = True

  for config_id, result in results.items():
    base_res, exp_res = (
      result.get(benchmark_job_pb2.AbTestGroup.BASELINE),
      result.get(benchmark_job_pb2.AbTestGroup.EXPERIMENT),
    )

    if not exp_res:
      sections.append(
        f"### {config_id}: FAILED (Experiment Missing)\nThe experiment"
        " benchmark job failed to produce results."
      )
      global_success = False
      continue
    if not base_res:
      sections.append(
        f"### {config_id}: Incomplete (Baseline Missing)\nValid comparison"
        " could not be made because the Baseline job failed."
      )
      continue

    b_stats = {(s.metric_name, s.stat): (s.value.value, s.unit) for s in base_res.stats}
    e_stats = {(s.metric_name, s.stat): (s.value.value, s.unit) for s in exp_res.stats}

    rows = []
    for metric_name, stat in sorted(set(b_stats.keys()) | set(e_stats.keys())):
      base_info = b_stats.get((metric_name, stat))
      exp_info = e_stats.get((metric_name, stat))
      base_val = base_info[0] if base_info else None
      exp_val = exp_info[0] if exp_info else None
      unit = (
        (exp_info[1] if exp_info else None) or (base_info[1] if base_info else "") or ""
      )

      thresh, direction = _get_comparison_config(
        matrix_map, config_id, metric_name, stat
      )

      is_reg = _is_ab_regression(base_val, exp_val, thresh, direction)
      if is_reg:
        global_success = False

      rows.append(
        _format_ab_metric_row(
          metric_name, stat, base_val, exp_val, thresh, direction, is_reg, unit=unit
        )
      )

    headers = [
      "Metric",
      (
        "Baseline <br>"
        f" ({markdown_formatter.format_commit_link(base_res.commit_sha, repo_url)})"
      ),
      (
        "Experiment <br>"
        f" ({markdown_formatter.format_commit_link(exp_res.commit_sha, repo_url)})"
      ),
      "Delta",
      "Threshold",
      "Status",
    ]
    sections.append(
      markdown_formatter.format_table(rows, headers=headers, title=config_id)
    )

  sections.append(f"**Global Status:** {'🟢 PASS' if global_success else '🔴 FAIL'}")
  return "\n\n".join(sections), global_success
