# Copyright 2025 Google LLC
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

"""
Library for performing static threshold analysis on a benchmark result.
"""

from collections.abc import Sequence
import re
import sys
from typing import TypedDict
from bap_proto import benchmark_result_pb2
from bap_proto.common import metric_pb2
from utils import markdown_formatter

ResultMap = dict[tuple[str, str], benchmark_result_pb2.ComputedStat]
MetricSpecs = Sequence[metric_pb2.MetricSpec]


class Regression(TypedDict):
  """Defines the structure for a reported regression."""

  config_id: str
  metric: str
  stat: str
  current: int | float
  baseline: int | float
  threshold: float
  unit: str


class Evaluation(TypedDict):
  """Defines the structure for an evaluated metric comparison check."""

  config_id: str
  metric: str
  stat: str
  current: float
  baseline: float
  threshold: float
  unit: str
  is_regression: bool


def _is_regression(
  current_value: float,
  baseline: float,
  threshold: float,
  direction: metric_pb2.ImprovementDirection,
) -> bool:
  """Checks if a metric value constitutes a performance regression."""
  tolerance = baseline * threshold

  if direction == metric_pb2.ImprovementDirection.LESS:
    return current_value > (baseline + tolerance)

  elif direction == metric_pb2.ImprovementDirection.GREATER:
    return current_value < (baseline - tolerance)

  else:
    # If direction is unspecified, we treat it as a strict equality check with tolerance
    return abs(current_value - baseline) > tolerance


def _resolve_matched_metrics(
  metric_spec: metric_pb2.MetricSpec,
  stat_name: str,
  result_map: ResultMap,
) -> list[str]:
  """Resolves concrete metric names matching the spec identifier and stat."""
  id_type = metric_spec.WhichOneof("identifier")
  if id_type == "name":
    return [metric_spec.name] if (metric_spec.name, stat_name) in result_map else []
  elif id_type == "pattern":
    regex = re.compile(metric_spec.pattern)
    return [
      m_name
      for m_name, s_name in result_map.keys()
      if s_name == stat_name and regex.search(m_name)
    ]
  return []


def _evaluate_metric(
  config_id: str,
  metric_name: str,
  stat_name: str,
  result_stat: benchmark_result_pb2.ComputedStat,
  comparison: metric_pb2.ComparisonSpec | None,
) -> Evaluation:
  """Evaluates a single metric and returns its evaluation summary."""
  current_val = result_stat.value.value
  unit = result_stat.unit

  if comparison is None:
    return {
      "config_id": config_id,
      "metric": metric_name,
      "stat": stat_name,
      "current": current_val,
      "baseline": None,
      "threshold": None,
      "unit": unit,
      "is_regression": False,
      "has_comparison": False,
    }

  baseline = comparison.baseline.value
  threshold = comparison.threshold.value
  is_reg = _is_regression(
    current_val, baseline, threshold, comparison.improvement_direction
  )

  return {
    "config_id": config_id,
    "metric": metric_name,
    "stat": stat_name,
    "current": current_val,
    "baseline": baseline,
    "threshold": threshold,
    "unit": unit,
    "is_regression": is_reg,
    "has_comparison": True,
  }


class StaticAnalyzer:
  """Performs static threshold analysis on a benchmark result."""

  def __init__(self, metric_specs: MetricSpecs):
    """Initializes the analyzer with the metric specifications."""
    self.metric_specs = metric_specs
    self.evaluations: list[Evaluation] = []
    self.has_regressions = False

  @property
  def regressions(self) -> list[Regression]:
    """Exposes regressions computed dynamically from evaluations."""
    return [
      {
        "config_id": item["config_id"],
        "metric": item["metric"],
        "stat": item["stat"],
        "current": item["current"],
        "baseline": item["baseline"],
        "threshold": item["threshold"] * 100,
        "unit": item["unit"],
      }
      for item in self.evaluations
      if item["is_regression"]
      and item["baseline"] is not None
      and item["threshold"] is not None
    ]

  def run_analysis(self, benchmark_result: benchmark_result_pb2.BenchmarkResult):
    """Run the threshold comparison."""
    result_map: ResultMap = {
      (stat.metric_name, metric_pb2.Stat.Name(stat.stat)): stat
      for stat in benchmark_result.stats
    }

    for metric_spec in self.metric_specs:
      for stat_spec in metric_spec.stats:
        stat_name = metric_pb2.Stat.Name(stat_spec.stat)
        matched_metrics = _resolve_matched_metrics(metric_spec, stat_name, result_map)

        if not matched_metrics:
          id_type = metric_spec.WhichOneof("identifier")
          identifier = metric_spec.pattern if id_type == "pattern" else metric_spec.name
          print(
            f"Warning: Skipping check for {identifier} ({stat_name}): Computed statistic not found in artifact.",
            file=sys.stderr,
          )
          continue

        comparison = stat_spec.comparison if stat_spec.HasField("comparison") else None
        for concrete_metric in matched_metrics:
          evaluation = _evaluate_metric(
            benchmark_result.config_id,
            concrete_metric,
            stat_name,
            result_map[(concrete_metric, stat_name)],
            comparison,
          )
          self.evaluations.append(evaluation)
          if evaluation["is_regression"]:
            self.has_regressions = True

  def generate_report_section(self, config_id: str) -> tuple[str, bool]:
    """Generates a Markdown report section table for the given config_id.

    Args:
        config_id: The benchmark configuration ID title for the section.

    Returns:
        A tuple containing (markdown_string, success), where success is True if
        there are no regressions in this section.
    """
    rows = []
    for item in self.evaluations:
      name = markdown_formatter.format_with_subtext(item["metric"], item["stat"])
      curr = markdown_formatter.format_float(item["current"])
      if item.get("has_comparison", True) and item["baseline"] is not None:
        rows.append([
          name,
          curr,
          markdown_formatter.format_float(item["baseline"]),
          markdown_formatter.format_percent(item["threshold"]),
          markdown_formatter.format_status(item["is_regression"]),
        ])
      else:
        rows.append([name, curr, "-", "-", markdown_formatter.format_status(None)])
    headers = ["Metric", "Current", "Baseline", "Threshold", "Status"]
    return (
      markdown_formatter.format_table(rows, headers=headers, title=config_id),
      not self.has_regressions,
    )
