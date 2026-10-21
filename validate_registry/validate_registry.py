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
import sys
from pathlib import Path

from validate_registry import validate_registry_lib


def main() -> None:
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
      print(f"Note: No actions found in registry: {args.registry_path}")
    else:
      print(f"Security Validation PASSED ({action_count} actions checked).")
  except FileNotFoundError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
  except validate_registry_lib.SecurityValidationError as e:
    print("\nSecurity Validation FAILED:", file=sys.stderr)
    for err in e.errors:
      print(f"  - {err}", file=sys.stderr)
    sys.exit(1)
  except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
  main()
