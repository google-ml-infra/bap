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

"""Fake benchmark script for E2E testing the reusable workflow. Logs metrics using tensorboardX."""

import logging
import os
import sys
from tensorboardX import SummaryWriter
from utils import logging_config

logger = logging.getLogger(__name__)


def main():
  """Runs a fake benchmark and writes TensorBoard logs."""
  logging_config.setup_logging()
  logger.info("E2E test benchmark script starting.")
  tblog_dir = os.environ.get("TENSORBOARD_OUTPUT_DIR")

  if not tblog_dir:
    logger.error("TENSORBOARD_OUTPUT_DIR env var not set.")
    sys.exit(1)

  logger.info("Received TENSORBOARD_OUTPUT_DIR: %s.", tblog_dir)
  args = sys.argv[1:]
  logger.info("Received runtime_flags: %s.", args)
  fake_metrics = [101.2, 100.5, 102.1, 99.8, 101.5]
  logger.info("Fake metrics generated: %s.", fake_metrics)

  try:
    writer = SummaryWriter(log_dir=tblog_dir)

    for i, value in enumerate(fake_metrics):
      writer.add_scalar("wall_time", value, global_step=i)

    writer.close()

    logger.info("Successfully wrote 5 wall_time metrics to %s", tblog_dir)
    logger.info("E2E test benchmark script finished.")

  except Exception as e:
    logger.error("Error writing TensorBoard logs: %s", e)
    sys.exit(1)


if __name__ == "__main__":
  main()
