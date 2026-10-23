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

"""Tests for centralized logging configuration."""

import logging
import sys
import pytest
from protovalidate import validate
from bap_proto.common import environment_config_pb2
from utils import logging_config


def test_setup_logging_sets_dependency_levels():
  """Verifies that noisy third-party loggers are set to WARNING."""
  logging_config.setup_logging(level=logging.DEBUG)

  for logger_name in logging_config.NOISY_DEPENDENCY_LOGGERS:
    assert logging.getLogger(logger_name).level == logging.WARNING


def test_setup_logging_suppresses_celpy_debug_noise(caplog):
  """Verifies that protovalidate/celpy debug logs are suppressed when setup_logging runs."""
  with caplog.at_level(logging.DEBUG):
    logging_config.setup_logging(level=logging.DEBUG)
    env_cfg = environment_config_pb2.EnvironmentConfig(
      id="cpu",
      runner_label="linux-x86-n2-32",
      container_image="gcr.io/testing/cpu:latest",
    )
    validate(env_cfg)

  celpy_records = [r for r in caplog.records if r.name.startswith("celpy")]
  assert celpy_records == []


if __name__ == "__main__":
  sys.exit(pytest.main(sys.argv))
