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

"""Centralized logging configuration for BAP Python tools."""

import logging

DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Third-party loggers that emit excessive debug noise (e.g. AST/CEL evaluation trees
# from protovalidate's underlying cel-python and lark libraries).
NOISY_DEPENDENCY_LOGGERS = (
  "celpy",
  "protovalidate",
  "lark",
)


def setup_logging(level: int | str = logging.INFO) -> None:
  """Configures the root logger and suppresses noisy third-party dependency loggers.

  Args:
      level: The logging level for the root logger (default: logging.INFO).
  """
  logging.basicConfig(
    level=level,
    format=DEFAULT_LOG_FORMAT,
    datefmt=DEFAULT_DATE_FORMAT,
  )
  for logger_name in NOISY_DEPENDENCY_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.WARNING)
