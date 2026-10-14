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

"""Fake benchmark script for E2E testing the reusable workflow. Logs metrics using TF 1.x Summary."""

import json
import logging
import os
import sys
import time

from tensorboard.compat.proto import event_pb2
from tensorboard.compat.proto import summary_pb2
from tensorboard.summary.writer.event_file_writer import EventFileWriter
from utils import logging_config

logger = logging.getLogger(__name__)


def main():
  """Runs a fake benchmark and writes TensorBoard logs + artifacts."""
  logging_config.setup_logging()
  logger.info("E2E test benchmark script starting.")
  tblog_dir = os.environ.get("TENSORBOARD_OUTPUT_DIR")
  artifact_dir = os.environ.get("WORKLOAD_ARTIFACTS_DIR")
  metadata_dir = os.environ.get("WORKLOAD_METADATA_DIR")

  if not tblog_dir:
    logger.error("TENSORBOARD_OUTPUT_DIR env var not set.")
    sys.exit(1)

  # Write TensorBoard metrics
  logger.info("Received TENSORBOARD_OUTPUT_DIR: %s.", tblog_dir)
  args = sys.argv[1:]
  logger.info("Received runtime_flags: %s.", args)
  fake_metrics = [101.2, 100.5, 102.1, 99.8, 101.5]

  try:
    writer = EventFileWriter(tblog_dir)

    for i, value in enumerate(fake_metrics):
      event = event_pb2.Event(
        step=i,
        wall_time=time.time(),
        summary=summary_pb2.Summary(
          value=[summary_pb2.Summary.Value(tag="wall_time", simple_value=value)]
        ),
      )
      writer.add_event(event)

    writer.close()

    logger.info("Successfully wrote 5 wall_time metrics to %s", tblog_dir)

    # Create workload artifact
    if artifact_dir:
      logger.info("Received WORKLOAD_ARTIFACTS_DIR: %s", artifact_dir)
      artifact_path = os.path.join(artifact_dir, "test_artifact.txt")
      with open(artifact_path, "w") as f:
        f.write("Hello from run_benchmark_summary_v1.")
      logger.info("Successfully wrote artifact to %s", artifact_path)
    else:
      logger.warning("WORKLOAD_ARTIFACTS_DIR env var not set.")

    # Create dynamic metadata
    if metadata_dir:
      logger.info("Received WORKLOAD_METADATA_DIR: %s", metadata_dir)
      metadata_path = os.path.join(metadata_dir, "workload_metadata.json")
      with open(metadata_path, "w") as f:
        json.dump({"driver_version": "535.100", "cuda_version": "12.2"}, f)
      logger.info("Successfully wrote dynamic metadata to %s", metadata_path)
    else:
      logger.warning("WORKLOAD_METADATA_DIR env var not set.")

    logger.info("E2E test benchmark script finished.")

  except Exception as e:
    logger.error("Error executing benchmark: %s", e)
    sys.exit(1)


if __name__ == "__main__":
  main()
