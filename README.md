# BAP (Benchmarking Automation Platform)

## What is BAP?

BAP is a GitHub-native automation platform designed to standardize performance
benchmarking and regression testing for open-source ML frameworks.

At its core, BAP provides a unified system for **defining**, **executing**, and
**tracking** benchmarks. It replaces bespoke tooling with a standardized loop:

-   **Define**: Declare benchmarks in a simple .pbtxt registry.
-   **Run**: Execute workloads (Python, Bazel, etc.) using a reusable GitHub
    Actions workflow.
-   **Collect**: Automatically parse and standardize metrics from TensorBoard
    logs.

## Key Features

BAP provides various capabilities for performance management:

-   **Static Threshold Analysis**: Automatically compares metrics against a
    baseline and fails CI jobs if a regression is detected.
-   **A/B Testing**: A dedicated mode for head-to-head performance comparisons
    in presubmit to isolate noise and detect regressions accurately.
-   **Downstream Consumer Integration**: Publishes results via Pub/Sub to
    supported consumers, including **Data Studio** (*Available Q3 2026*) for public dashboards.

## Users

BAP is currently trusted by core ML frameworks to automate their OSS performance benchmarks.

<p>BAP supports benchmarking for the following public repositories:</p>
<ul>
  <li><a href="https://github.com/openxla/xla">openxla/xla</a></li>
  <li><a href="https://github.com/openxla/tokamax">openxla/tokamax</a></li>
  <li><a href="https://github.com/google/tpu-raiden">google/tpu-raiden</a></li>
</ul>

## Getting Started

-   [Onboarding Guide](docs/onboarding.md): Step-by-step guide for
    setting up a benchmark registry and configuring workflows using BAP.

