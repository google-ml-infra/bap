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

"""Tests for metric_parser utility library."""

import sys
import pytest
from bap_proto.common import metric_pb2
from utils import metric_parser


def test_matches_metric_spec_name():
  spec = metric_pb2.MetricSpec(name="latency")
  assert metric_parser.matches_metric_spec(spec, "latency")
  assert not metric_parser.matches_metric_spec(spec, "latency_p99")


def test_matches_metric_spec_pattern():
  spec = metric_pb2.MetricSpec(pattern=r"torch_tpu/.*/step_time")
  assert metric_parser.matches_metric_spec(spec, "torch_tpu/resnet50/step_time")
  assert not metric_parser.matches_metric_spec(spec, "torch_tpu/resnet50/loss")


def test_matches_metric_spec_unset():
  spec = metric_pb2.MetricSpec()
  assert not metric_parser.matches_metric_spec(spec, "latency")


def test_get_metric_identifier():
  name_spec = metric_pb2.MetricSpec(name="latency")
  pattern_spec = metric_pb2.MetricSpec(pattern=r"wall_.*")
  assert metric_parser.get_metric_identifier(name_spec) == "latency"
  assert metric_parser.get_metric_identifier(pattern_spec) == r"wall_.*"


def test_parse_metric_specs_from_json():
  raw = '[{"name": "latency", "unit": "ms"}, {"pattern": "wall_.*"}]'
  specs = metric_parser.parse_metric_specs_from_json(raw)
  assert len(specs) == 2
  assert specs[0].name == "latency"
  assert specs[1].pattern == "wall_.*"
  assert metric_parser.parse_metric_specs_from_json("") == []
  assert metric_parser.parse_metric_specs_from_json("null") == []


if __name__ == "__main__":
  sys.exit(pytest.main(sys.argv))
