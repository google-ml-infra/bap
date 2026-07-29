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

"""Tests for common markdown formatting utilities."""

import sys
import pytest
from utils import markdown_formatter


def test_format_with_subtext():
  assert (
    markdown_formatter.format_with_subtext("wall_time", "MEAN")
    == "wall_time <small>(MEAN)</small>"
  )


def test_format_float():
  assert markdown_formatter.format_float(None) == "-"
  assert markdown_formatter.format_float(12.34567) == "12.3457"
  assert markdown_formatter.format_float(12.34567, precision=2) == "12.35"


def test_format_percent():
  assert markdown_formatter.format_percent(None) == "-"
  assert markdown_formatter.format_percent(0.05) == "5%"
  assert markdown_formatter.format_percent(0.0543, precision=2, signed=True) == "+5.43%"
  assert (
    markdown_formatter.format_percent(-0.0543, precision=2, signed=True) == "-5.43%"
  )


def test_format_header():
  assert markdown_formatter.format_header("Title", level=1) == "# Title"
  assert markdown_formatter.format_header("Section", level=3) == "### Section"


def test_format_table():
  rendered = markdown_formatter.format_table(
    [["wall_time", "100.0"]],
    ["Metric", "Value"],
    title="Test Header",
    title_level=3,
  )
  assert "### Test Header" in rendered
  assert "Metric" in rendered
  assert "Value" in rendered
  assert "wall_time" in rendered


def test_format_commit_link():
  assert (
    markdown_formatter.format_commit_link(None, "https://github.com/org/repo")
    == "unknown"
  )
  assert (
    markdown_formatter.format_commit_link(
      "abcdef123456", "https://github.com/org/repo/"
    )
    == "[abcdef1](https://github.com/org/repo/commit/abcdef123456)"
  )


def test_format_status():
  assert markdown_formatter.format_status(True) == "🔴 REGRESSION"
  assert markdown_formatter.format_status(False) == "🟢 PASS"
  assert markdown_formatter.format_status(None) == "ℹ️ INFO"
  assert markdown_formatter.format_status(None, missing_exp=True) == "🔴 MISSING"
  assert markdown_formatter.format_status(None, missing_base=True) == "🔵 NEW"
  assert markdown_formatter.format_status(None, undetermined=True) == "🟡 UNDETERMINED"


if __name__ == "__main__":
  sys.exit(pytest.main(sys.argv))
