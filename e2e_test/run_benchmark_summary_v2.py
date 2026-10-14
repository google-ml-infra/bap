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

"""Fake benchmark script for E2E testing the reusable workflow. Logs metrics using TF 2.x Summary."""

import logging
import os
import sys
import tensorflow as tf
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

  e2e_test_var = os.environ.get("E2E_TEST_VAR")
  another_var = os.environ.get("ANOTHER_VAR")

  if e2e_test_var:
    logger.info("Received E2E_TEST_VAR: %s.", e2e_test_var)
    if e2e_test_var != "hello_from_e2e_test":
      logger.error(
        "E2E_TEST_VAR expected 'hello_from_e2e_test', got '%s'",
        e2e_test_var,
      )
      sys.exit(1)

  if another_var:
    logger.info("Received ANOTHER_VAR: %s.", another_var)
    if another_var != "123":
      logger.error("ANOTHER_VAR expected '123', got '%s'", another_var)
      sys.exit(1)

  args = sys.argv[1:]
  logger.info("Received runtime_flags: %s.", args)
  fake_metrics = [101.2, 100.5, 102.1, 99.8, 101.5]
  logger.info("Fake metrics generated: %s.", fake_metrics)

  try:
    writer = tf.summary.create_file_writer(tblog_dir)

    with writer.as_default():
      for i, value in enumerate(fake_metrics):
        tf.summary.scalar("wall_time", value, step=i)

    writer.flush()
    writer.close()

    logger.info("Successfully wrote 5 wall_time metrics to %s", tblog_dir)
    logger.info("E2E test benchmark script finished.")

  except Exception as e:
    logger.error("Error writing TensorBoard logs: %s", e)
    sys.exit(1)


if __name__ == "__main__":
  main()
