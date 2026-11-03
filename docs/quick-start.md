# BAP Quick Start Guide

This guide provides step-by-step instructions and minimal examples for onboarding a repository to the Benchmarking Automation Platform (BAP).

## Prerequisites

Before onboarding, ensure the repository has a workload (e.g., a Python script or Bazel target) that outputs metrics. BAP requires metrics to be written as TensorBoard event files to the directory specified by the `TENSORBOARD_OUTPUT_DIR` environment variable.

## Steps to Onboard

### 1. Create the GitHub Actions Workflow

Create a new workflow file at `.github/workflows/run-benchmarks.yaml` in your repository using the reusable BAP workflow.

```yaml
name: Run presubmit benchmarks

on:
  pull_request:
    paths:
      - './**'
  workflow_dispatch:

permissions:
  contents: read
  pull-requests: write

jobs:
  run_benchmarks:
    uses: google-ml-infra/bap/.github/workflows/run_benchmarks.yml@main
    with:
      registry_file: "perflab/benchmark_registry.pbtxt" # e.g. torch_tpu uses perflab/
      ab_mode: true
      post_pr_comment: true
```

*Note: You can change the trigger or the `registry_file` path depending on your project structure.*

### 2. Create the Benchmark Registry

Create a `.pbtxt` file (e.g., `perflab/benchmark_registry.pbtxt`). Define the workloads, environments, and metrics based on your needs.

**Example for a Python workload:**
```proto
benchmarks {
  name: "example_benchmark"
  description: "Example Python benchmark"
  owner: "my-team"

  workload {
    # Reference the standard Python executor from BAP
    action: "google-ml-infra/bap/./actions/workload_executors/python@main"
    action_inputs { key: "python_version" value: "3.11" }
    action_inputs { key: "script_path" value: "my_benchmark_script.py" }
    action_inputs { key: "runtime_flags" value: "--my_flag" }
  }

  environment_configs {
    id: "cpu_standard"
    runner_label: "linux-x86-n4-16"
  }

  metrics {
    # REQUIRED: Must exactly match the TensorBoard tag name
    name: "wall_time"
    unit: "ms"
    stats {
      stat: MEAN
      comparison: {
        baseline { value: 100.0 }
        threshold { value: 0.1 } # 10% tolerance
        improvement_direction: LESS
      }
    }
  }
}
```

### 3. Verify Metric Logging in the Workload

Check your benchmark script to ensure it logs metrics correctly:
- It must read the `TENSORBOARD_OUTPUT_DIR` environment variable.
- It must write TensorBoard event files to that directory.
- The logged metric tag (e.g., `"wall_time"`) must exactly match the `name` in the registry's `metrics` block.

**Example Python Snippet:**
```python
import os
from tensorboardX import SummaryWriter

tblog_dir = os.environ.get("TENSORBOARD_OUTPUT_DIR")
if tblog_dir:
  writer = SummaryWriter(tblog_dir)
  # Log your metric (tag name must match registry)
  writer.add_scalar("wall_time", 95.5, global_step=0)
  writer.close()
```
