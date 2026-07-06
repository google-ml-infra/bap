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

"""Tests for the GitHub Actions matrix generator."""

import sys
from unittest import mock
import pytest
from google.protobuf import text_format
from gh_matrix_generator import gh_matrix_generator_lib
from bap_proto import benchmark_registry_pb2

# --- Test Data ---

VALID_SUITE_PBTXT = """
    benchmarks {
      name: "cpu_benchmark"
      description: "A valid CPU benchmark."
      owner: "cpu-team"
      tags: "team-cpu"
      workload {
        action: "./ml_actions/actions/workload_executors/bazel"
        action_inputs { key: "target" value: "//b:cpu" }
        action_inputs { key: "runtime_flags" value: "--model_name=cpu_model" }
      }
      environment_configs {
        id: "basic_cpu"
        runner_label: "linux-x86-n2-32"
        container_image: "gcr.io/testing/cpu-container:latest"
        tags: ["presubmit", "postsubmit", "cpu"]
        workload_action_inputs { key: "runtime_flags_hw" value: "--precision=fp32" }
      }
      metrics {
        name: "wall_time_ms"
        unit: "ms"
        stats {
          stat: MEDIAN
          comparison: {
            baseline { value: 500.0 }
            threshold { value: 0.05 }
            improvement_direction: LESS
          }
        }
      }
    }
    benchmarks {
      name: "gpu_benchmark"
      description: "A valid GPU benchmark."
      owner: "gpu-team"
      tags: "team-gpu"
      workload {
        action: "./user_repo/actions/hlo"
        action_inputs { key: "gcs_path" value: "gs://bucket/model.hlo" }
        action_inputs { key: "iterations" value: "100" }
      }
      environment_configs {
        id: "a100_4gpu"
        runner_label: "linux-x86-a2-48-a100-4gpu"
        container_image: "gcr.io/testing/gpu-container:latest"
        tags: ["presubmit", "gpu"]
      }
    }
    """

# Missing environment configuration ID.
INVALID_SUITE_MISSING_ID_PBTXT = """
    benchmarks {
      name: "broken_benchmark"
      description: "Missing environment_config ID."
      owner: "cpu-team"
      workload {
        action: "./ml_actions/actions/workload_executors/bazel"
      }
      environment_configs {
        runner_label: "linux-x86-n2-32"
        container_image: "gcr.io/testing/cpu-container:latest"
        tags: ["presubmit"]
      }
    }
    """

# --- Tests for Validation Logic ---


@mock.patch("builtins.open", new_callable=mock.mock_open, read_data=VALID_SUITE_PBTXT)
@mock.patch("os.path.isabs", return_value=True)
def test_load_and_validate_suite_success(_mock_isabs, _mock_open):
  """Tests that a valid benchmark registry pbtxt file is loaded and validated correctly."""
  suite = gh_matrix_generator_lib.load_and_validate_suite_from_pbtxt("dummy_path.pbtxt")
  assert len(suite.benchmarks) == 2
  assert suite.benchmarks[0].name == "cpu_benchmark"


@mock.patch(
  "builtins.open",
  new_callable=mock.mock_open,
  read_data=INVALID_SUITE_MISSING_ID_PBTXT,
)
@mock.patch("os.path.isabs", return_value=True)
def test_load_and_validate_suite_fails_on_invalid_pbtxt(_mock_isabs, _mock_open):
  """Tests that an invalid benchmark registry pbtxt file fails validation."""
  with pytest.raises(ValueError) as excinfo:
    gh_matrix_generator_lib.load_and_validate_suite_from_pbtxt("invalid.pbtxt")

  error_msg = str(excinfo.value)
  assert "benchmarks.environment_configs.id" in error_msg
  assert "Registry file 'invalid.pbtxt' is invalid" in error_msg


# --- Tests for Matrix Generation Logic ---


@pytest.mark.parametrize(
  "tag_filter, expected_count, expected_names",
  [
    (["presubmit"], 2, {"cpu_benchmark", "gpu_benchmark"}),
    (["postsubmit"], 1, {"cpu_benchmark"}),
    (["gpu"], 1, {"gpu_benchmark"}),
    (["team-cpu"], 1, {"cpu_benchmark"}),
    ([], 2, {"cpu_benchmark", "gpu_benchmark"}),
    (["nonexistent"], 0, set()),
  ],
)
def test_generate_matrix_tag_filtering(tag_filter, expected_count, expected_names):
  """Tests that the matrix is correctly filtered by tags."""
  suite = text_format.Parse(VALID_SUITE_PBTXT, benchmark_registry_pb2.BenchmarkSuite())

  generator = gh_matrix_generator_lib.MatrixGenerator()
  matrix = generator.generate(
    suite, github_event="workflow_dispatch", tag_filter=tag_filter
  )

  assert len(matrix) == expected_count
  generated_names = {entry["benchmark_name"] for entry in matrix}
  assert generated_names == expected_names


@pytest.mark.parametrize(
  "benchmark_filter, expected_count, expected_names",
  [
    ("cpu", 1, {"cpu_benchmark"}),
    ("gpu", 1, {"gpu_benchmark"}),
    ("benchmark", 2, {"cpu_benchmark", "gpu_benchmark"}),
    ("xyz_nomatch", 0, set()),
  ],
)
def test_generate_matrix_benchmark_filtering(
  benchmark_filter, expected_count, expected_names
):
  """Tests that the matrix is correctly filtered by benchmark name regex."""
  suite = text_format.Parse(VALID_SUITE_PBTXT, benchmark_registry_pb2.BenchmarkSuite())

  generator = gh_matrix_generator_lib.MatrixGenerator()
  matrix = generator.generate(
    suite, github_event="workflow_dispatch", benchmark_filter=benchmark_filter
  )

  assert len(matrix) == expected_count
  generated_names = {entry["benchmark_name"] for entry in matrix}
  assert generated_names == expected_names


@pytest.mark.parametrize(
  "environment_filter, expected_count, expected_names",
  [
    ("basic_cpu", 1, {"cpu_benchmark"}),
    ("a100", 1, {"gpu_benchmark"}),
    ("nomatch", 0, set()),
  ],
)
def test_generate_matrix_environment_filtering(
  environment_filter, expected_count, expected_names
):
  """Tests that the matrix is correctly filtered by environment configuration ID regex."""
  suite = text_format.Parse(VALID_SUITE_PBTXT, benchmark_registry_pb2.BenchmarkSuite())

  generator = gh_matrix_generator_lib.MatrixGenerator()
  matrix = generator.generate(
    suite, github_event="workflow_dispatch", environment_filter=environment_filter
  )

  assert len(matrix) == expected_count
  generated_names = {entry["benchmark_name"] for entry in matrix}
  assert generated_names == expected_names


@pytest.mark.parametrize(
  "github_event, expected_type",
  [
    ("pull_request", "PRESUBMIT"),
    ("schedule", "SCHEDULED"),
    ("push", "POSTSUBMIT"),
    ("release", "POSTSUBMIT"),
    ("workflow_dispatch", "MANUAL"),
    ("random_event", "MANUAL"),
  ],
)
def test_generate_matrix_workflow_type_inference(github_event, expected_type):
  """Tests that github_event correctly maps to workflow_type in the output."""
  suite = text_format.Parse(VALID_SUITE_PBTXT, benchmark_registry_pb2.BenchmarkSuite())
  generator = gh_matrix_generator_lib.MatrixGenerator()

  matrix = generator.generate(suite, github_event=github_event, tag_filter=["cpu"])

  # Check the first job in the matrix
  assert matrix[0]["workflow_type"] == expected_type


def test_generate_matrix_content_correctness():
  """Tests that the matrix entry contains the correct fields and config IDs."""
  suite = text_format.Parse(VALID_SUITE_PBTXT, benchmark_registry_pb2.BenchmarkSuite())

  generator = gh_matrix_generator_lib.MatrixGenerator()
  matrix = generator.generate(suite, github_event="pull_request", tag_filter=["cpu"])

  cpu_entry = next(item for item in matrix if item["benchmark_name"] == "cpu_benchmark")

  # Ensure standard mode does not have A/B testing keys
  assert "ab_test_group" not in cpu_entry
  assert "checkout_ref" not in cpu_entry

  assert cpu_entry["config_id"] == "cpu_benchmark_basic_cpu"
  assert cpu_entry["workflow_type"] == "PRESUBMIT"

  assert cpu_entry["environment_config"]["id"] == "basic_cpu"
  assert cpu_entry["environment_config"]["runner_label"] == "linux-x86-n2-32"
  assert (
    cpu_entry["environment_config"]["container_image"]
    == "gcr.io/testing/cpu-container:latest"
  )

  action_inputs = cpu_entry["workload"]["action_inputs"]
  assert action_inputs["target"] == "//b:cpu"
  assert action_inputs["runtime_flags_hw"] == "--precision=fp32"


# --- Tests for A/B Testing Logic ---


def test_generate_matrix_ab_mode(subtests):
  """Tests that A/B mode duplicates entries and assigns correct refs."""
  suite = text_format.Parse(VALID_SUITE_PBTXT, benchmark_registry_pb2.BenchmarkSuite())

  generator = gh_matrix_generator_lib.MatrixGenerator()
  # Run in A/B Mode with custom refs.
  matrix = generator.generate(
    suite,
    github_event="workflow_dispatch",
    benchmark_filter="cpu_benchmark",
    ab_mode=True,
    baseline_ref="main",
    experiment_ref="feat-123",
  )

  # Expect 2 entries (1 benchmark * 2 modes)
  assert len(matrix) == 2

  baseline = matrix[0]
  experiment = matrix[1]

  # Verify baseline
  with subtests.test(msg="baseline"):
    assert baseline["benchmark_name"] == "cpu_benchmark"
    assert baseline["ab_test_group"] == "BASELINE"
    assert baseline["checkout_ref"] == "main"
    assert baseline["config_id"] == "cpu_benchmark_basic_cpu"

  # Verify experiment
  with subtests.test(msg="experiment"):
    assert experiment["benchmark_name"] == "cpu_benchmark"
    assert experiment["ab_test_group"] == "EXPERIMENT"
    assert experiment["checkout_ref"] == "feat-123"
    assert experiment["config_id"] == "cpu_benchmark_basic_cpu"


def test_generate_matrix_ab_mode_presubmit(subtests):
  """Tests A/B mode with multiple benchmarks.."""
  suite = text_format.Parse(VALID_SUITE_PBTXT, benchmark_registry_pb2.BenchmarkSuite())

  generator = gh_matrix_generator_lib.MatrixGenerator()
  # Presubmit tag selects both CPU and GPU benchmarks.
  matrix = generator.generate(
    suite,
    github_event="pull_request",
    tag_filter=["presubmit"],
    ab_mode=True,
    baseline_ref="main",
    experiment_ref="HEAD",
  )

  # Expect 4 entries (2 benchmarks * 2 modes)
  assert len(matrix) == 4

  # Check we have baseline/experiment for both benchmarks
  groups = [entry["ab_test_group"] for entry in matrix]
  names = [entry["benchmark_name"] for entry in matrix]

  with subtests.test(msg="Verify groups"):
    assert groups.count("BASELINE") == 2
    assert groups.count("EXPERIMENT") == 2

  with subtests.test(msg="Verify benchmarks"):
    assert names.count("cpu_benchmark") == 2
    assert names.count("gpu_benchmark") == 2


def test_generate_matrix_colocated_ab_mode():
  """Tests that A/B Colocated benchmarks generate a single job with both refs."""
  colocated_pbtxt = """
    benchmarks {
      name: "colocated_bench"
      description: "An A/B Colocated benchmark."
      owner: "perf-team"
      ab_strategy: COLOCATED
      workload {
        action: "./ml_actions/actions/workload_executors/python"
      }
      environment_configs {
        id: "tpu_host"
        runner_label: "linux-x86-ct5lp"
        container_image: "gcr.io/testing/tpu-container:latest"
      }
    }
  """
  suite = text_format.Parse(colocated_pbtxt, benchmark_registry_pb2.BenchmarkSuite())
  generator = gh_matrix_generator_lib.MatrixGenerator()

  matrix = generator.generate(
    suite,
    github_event="pull_request",
    ab_mode=True,
    baseline_ref="main",
    experiment_ref="patch-1",
  )

  # Expect 1 entry (A/B Colocated mode emits a single job)
  assert len(matrix) == 1
  job = matrix[0]

  assert job["benchmark_name"] == "colocated_bench"
  assert job["ab_test_group"] == "COLOCATED"
  assert job["baseline_ref"] == "main"
  assert job["experiment_ref"] == "patch-1"
  # checkout_ref should not be set
  assert "checkout_ref" not in job


def test_generate_matrix_teardown_propagation():
  """Tests that the teardown input is correctly passed through."""
  teardown_pbtxt = """
    benchmarks {
      name: "teardown_bench"
      description: "A benchmark with teardown."
      owner: "perf-team"
      workload {
        action: "./ml_actions/actions/workload_executors/python"
        action_inputs {
          key: "script_path"
          value: "run.py"
        }
        action_inputs {
          key: "teardown"
          value: "true"
        }
      }
      environment_configs {
        id: "tpu_host"
        runner_label: "linux-x86-ct5lp"
        container_image: "gcr.io/testing/tpu-container:latest"
      }
    }
  """
  suite = text_format.Parse(teardown_pbtxt, benchmark_registry_pb2.BenchmarkSuite())
  generator = gh_matrix_generator_lib.MatrixGenerator()

  matrix = generator.generate(suite, github_event="push")

  assert len(matrix) == 1
  job = matrix[0]

  # Input should be present in action_inputs
  assert job["workload"]["action_inputs"]["teardown"] == "true"
  assert job["workload"]["action_inputs"]["script_path"] == "run.py"


def test_generate_matrix_teardown_default_colocated():
  """Tests that teardown defaults to 'true' for A/B Colocated benchmarks."""
  colocated_pbtxt = """
    benchmarks {
      name: "default_teardown_bench"
      description: "A colocated benchmark with default teardown."
      owner: "perf-team"
      ab_strategy: COLOCATED
      workload {
        action: "./ml_actions/actions/workload_executors/python"
      }
      environment_configs {
        id: "tpu_host"
        runner_label: "linux-x86-ct5lp"
        container_image: "gcr.io/testing/tpu-container:latest"
      }
    }
  """
  suite = text_format.Parse(colocated_pbtxt, benchmark_registry_pb2.BenchmarkSuite())
  generator = gh_matrix_generator_lib.MatrixGenerator()

  matrix = generator.generate(suite, github_event="push")

  job = matrix[0]
  # Should default to 'true' in action_inputs because it's COLOCATED
  assert job["workload"]["action_inputs"]["teardown"] == "true"


def test_generate_matrix_teardown_explicit_false_colocated():
  """Tests that explicit 'false' for teardown is respected even for COLOCATED."""
  colocated_pbtxt = """
    benchmarks {
      name: "false_teardown_bench"
      description: "A colocated benchmark with explicit false teardown."
      owner: "perf-team"
      ab_strategy: COLOCATED
      workload {
        action: "./ml_actions/actions/workload_executors/python"
        action_inputs {
          key: "teardown"
          value: "false"
        }
      }
      environment_configs {
        id: "tpu_host"
        runner_label: "linux-x86-ct5lp"
        container_image: "gcr.io/testing/tpu-container:latest"
      }
    }
  """
  suite = text_format.Parse(colocated_pbtxt, benchmark_registry_pb2.BenchmarkSuite())
  generator = gh_matrix_generator_lib.MatrixGenerator()

  matrix = generator.generate(suite, github_event="push")

  job = matrix[0]
  # Explicit 'false' should be respected
  assert job["workload"]["action_inputs"]["teardown"] == "false"


if __name__ == "__main__":
  sys.exit(pytest.main(sys.argv))
