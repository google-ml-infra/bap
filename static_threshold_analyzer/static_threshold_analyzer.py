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

"""Script to perform static threshold analysis on benchmark results."""

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import sys
from google.protobuf import json_format
from bap_proto import benchmark_job_pb2
from bap_proto import benchmark_result_pb2
from static_threshold_analyzer.static_threshold_analyzer_lib import (
  StaticAnalyzer,
)


def load_results(
  results_dir: Path,
) -> Mapping[str, benchmark_result_pb2.BenchmarkResult]:
  """Scans results_dir for benchmark_result.json files and parses them into BenchmarkResult protos mapped by config_id."""
  results: dict[str, benchmark_result_pb2.BenchmarkResult] = {}
  for path in results_dir.rglob("benchmark_result.json"):
    try:
      with open(path, "r") as f:
        data = json.load(f)
      result_proto = benchmark_result_pb2.BenchmarkResult()
      json_format.ParseDict(data, result_proto, ignore_unknown_fields=True)
      if result_proto.config_id:
        results[result_proto.config_id] = result_proto
    except json.JSONDecodeError as e:
      raise ValueError(f"Error decoding JSON for {path}: {e}") from e
    except json_format.ParseError as e:
      raise ValueError(f"Error parsing proto for {path}: {e}") from e
  return results


def main():
  parser = argparse.ArgumentParser(
    description="Analyze static threshold benchmark results."
  )
  parser.add_argument(
    "--matrix_json",
    required=True,
    help="Raw JSON string containing a list of BenchmarkJob protos.",
  )
  parser.add_argument(
    "--results_dir",
    required=True,
    type=Path,
    help="Directory containing downloaded benchmark result artifacts.",
  )
  parser.add_argument(
    "--output_file",
    required=True,
    type=Path,
    help="Output path for the markdown report.",
  )
  parser.add_argument(
    "--workflow_name",
    required=True,
    help="The name of the GitHub Actions workflow.",
  )
  parser.add_argument(
    "--repo_url",
    required=False,
    default="",
    help="Optional base URL of the repository.",
  )

  args = parser.parse_args()

  if not args.results_dir.is_dir():
    raise ValueError(f"{args.results_dir} is not a valid directory.")

  if not args.matrix_json or not args.matrix_json.strip():
    raise ValueError("matrix_json argument cannot be empty.")

  try:
    matrix_list = json.loads(args.matrix_json)
  except json.JSONDecodeError as e:
    raise ValueError(f"Provided matrix JSON is not valid: {e}") from e

  matrix_map: dict[str, benchmark_job_pb2.BenchmarkJob] = {}
  try:
    for job_dict in matrix_list:
      job = benchmark_job_pb2.BenchmarkJob()
      json_format.ParseDict(job_dict, job, ignore_unknown_fields=True)
      matrix_map[job.config_id] = job
  except json_format.ParseError as e:
    raise ValueError(
      f"Error parsing benchmark job JSON into BenchmarkJob proto: {e}"
    ) from e

  results = load_results(args.results_dir)

  lines: list[str] = [f"## Static Threshold Analysis: {args.workflow_name}"]
  global_success = True

  for config_id, job in matrix_map.items():
    if config_id in results:
      result = results[config_id]
      analyzer = StaticAnalyzer(list(job.metrics))
      analyzer.run_analysis(result)
      section_md, is_success = analyzer.generate_report_section(config_id)
      lines.append("\n" + section_md)
      if not is_success:
        global_success = False
    else:
      lines.append(
        f"\n### {config_id}\n_No benchmark results found. The workload may have crashed, timed out, or failed prior to reporting._"
      )
      global_success = False

  status_msg = "🟢 PASS" if global_success else "🔴 FAIL"
  lines.append(f"\n**Global Status:** {status_msg}")

  report_content = "\n".join(lines)
  args.output_file.write_text(report_content)
  print(f"Report written to {args.output_file}")

  if not global_success:
    print("Regressions detected!", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
  main()
