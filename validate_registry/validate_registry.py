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

"""CLI entrypoint for validating a benchmark registry for SSCI security compliance."""

import argparse
import logging
from pathlib import Path
import sys

from utils import logging_config
from validate_registry import validate_registry_lib

logger = logging.getLogger(__name__)


def main() -> None:
  logging_config.setup_logging()
  parser = argparse.ArgumentParser(
    description="Validates a benchmark registry for SSCI security compliance."
  )
  parser.add_argument(
    "registry_path",
    type=Path,
    help="Path to the .pbtxt benchmark registry file.",
  )
  args = parser.parse_args()

  try:
    action_count = validate_registry_lib.validate_external_file(args.registry_path)
    if action_count == 0:
      logger.info("No actions found in registry: %s", args.registry_path)
    else:
      logger.info("Security Validation PASSED (%d actions checked).", action_count)
  except FileNotFoundError as e:
    logger.error("%s", e)
    sys.exit(1)
  except validate_registry_lib.SecurityValidationError as e:
    logger.error("Security Validation FAILED:")
    for err in e.errors:
      logger.error("  - %s", err)
    sys.exit(1)
  except Exception as e:
    logger.error("%s", e)
    sys.exit(1)


if __name__ == "__main__":
  main()
