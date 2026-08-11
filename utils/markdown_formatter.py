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

"""Common, domain-agnostic utilities for markdown report formatting."""

from typing import Any
from tabulate import tabulate


def format_with_subtext(text: str, subtext: str) -> str:
  """Formats text with a smaller subtext in parentheses.

  Args:
      text: Main text string (e.g., metric name).
      subtext: Subtext string to place inside small parentheses (e.g., stat name).

  Returns:
      HTML-formatted string with small subtext.
  """
  return f"{text} <small>({subtext})</small>"


def format_float(val: float | None, precision: int = 4, unit: str = "") -> str:
  """Formats a float to a specified decimal precision, or '-' if None.

  Args:
      val: Floating-point value to format, or None.
      precision: Number of decimal places to include.
      unit: Optional unit string to append (e.g., 'ms', 's').

  Returns:
      Formatted float string with unit or '-' if None.
  """
  if val is None:
    return "-"
  formatted = f"{val:.{precision}f}"
  return f"{formatted} {unit}".strip()


def format_percent(val: float | None, precision: int = 0, signed: bool = False) -> str:
  """Formats a percentage value, or '-' if None.

  Args:
      val: Percentage decimal value (e.g., 0.05 for 5%), or None.
      precision: Number of decimal places.
      signed: Whether to prefix positive numbers with '+'.

  Returns:
      Formatted percentage string or '-' if None.
  """
  if val is None:
    return "-"
  if val == 0:
    return f"{0.0:.{precision}%}"
  sign = "+" if signed else ""
  return f"{val:{sign}.{precision}%}"


def format_header(title: str, level: int = 3) -> str:
  """Formats a title into a markdown header of specified level.

  Args:
      title: Header text string.
      level: Markdown header level (1 for H1 '#', 3 for H3 '###').

  Returns:
      Formatted markdown header line.
  """
  return f"{'#' * level} {title}"


def format_status(
  is_regression: bool | None,
  missing_exp: bool = False,
  missing_base: bool = False,
  undetermined: bool = False,
) -> str:
  """Generates standard emoji status badges for benchmark reports.

  Args:
      is_regression: Boolean indicating if metric regressed, or None for info-only metrics.
      missing_exp: True if experiment result was missing.
      missing_base: True if baseline result was missing.
      undetermined: True if change could not be determined (e.g. 0 baseline).

  Returns:
      Emoji status string (e.g. "🟢 PASS", "🔴 REGRESSION", "🔴 MISSING", "🔵 NEW", "🟡 UNDETERMINED", "ℹ️ INFO").
  """
  if missing_exp:
    return "🔴 MISSING"
  if missing_base:
    return "🔵 NEW"
  if undetermined:
    return "🟡 UNDETERMINED"
  if is_regression is None:
    return "ℹ️ INFO"
  return "🔴 REGRESSION" if is_regression else "🟢 PASS"


def format_commit_link(commit_sha: str | None, repo_url: str) -> str:
  """Generates a Markdown-formatted link to a commit SHA.

  Args:
      commit_sha: Full git commit SHA hash, or None.
      repo_url: Base repository web URL (e.g., "https://github.com/org/repo").

  Returns:
      Markdown link string like "[abcdef1](https://github.com/org/repo/commit/abcdef1...)"
      or "unknown" if commit_sha is None/empty.
  """
  if not commit_sha:
    return "unknown"
  short_sha = commit_sha[:7]
  clean_repo_url = repo_url.rstrip("/")
  return f"[{short_sha}]({clean_repo_url}/commit/{commit_sha})"


def format_table(
  rows: list[list[Any]],
  headers: list[str],
  title: str | None = None,
  title_level: int = 3,
  colalign: list[str] | None = None,
) -> str:
  """Formats a 2D list of rows into a GitHub-flavored Markdown table.

  Args:
      rows: 2D list of row cell values.
      headers: List of column header strings.
      title: Optional section title above the table.
      title_level: Header level for the title (default 3 '###').
      colalign: Optional list of column alignments ('left', 'right', 'center').

  Returns:
      Formatted Markdown string containing the optional title and table.
  """
  header = f"{format_header(title, title_level)}\n\n" if title else ""
  align = (
    colalign
    if colalign is not None
    else (
      ["left"] + ["right"] * (len(headers) - 2) + ["center"]
      if len(headers) >= 2
      else None
    )
  )
  table_md = tabulate(
    rows,
    headers=headers,
    tablefmt="github",
    disable_numparse=True,
    colalign=align,
  )
  return f"{header}{table_md}"
