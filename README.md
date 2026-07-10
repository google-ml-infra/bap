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
    for consumption.

## Getting Started

-   [Onboarding Guide](docs/onboarding.md): Step-by-step guide for
    setting up a benchmark registry and configuring workflows using BAP.

