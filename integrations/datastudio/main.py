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

"""Cloud Function for ingesting benchmark results into BigQuery.

Environment Variables:
    - DATASET_ID: Required. The BigQuery dataset ID where benchmark results are written
      (into `<project_id>.<dataset_id>.raw_benchmark_results`). Must not contain hyphens.
      (e.g., via Terraform, `gcloud functions deploy --set-env-vars`, or container env vars).
    - TEAM_GITHUB_REPO: Required. The repository name in 'org/repo' format (e.g. 'google-ml-infra/bap').
      Used to filter incoming Pub/Sub events so only matching messages are ingested.
    - PROJECT_ID: Optional. GCP project ID for BigQuery. If not set, defaults to the project ID
      associated with the BigQuery client service account / application default credentials.
    - PORT: Optional. HTTP port used by Functions Framework (defaults to "8080").

    Environment variables are injected into this script during deployment via terraform
"""

import base64
import binascii
import functools
import json
import logging
import os
from cloudevents.http import CloudEvent
import functions_framework
from google.cloud import bigquery
from google.protobuf import json_format
from protovalidate import ValidationError, Validator

from bap_proto import benchmark_result_pb2
from bap_proto.common import workflow_type_pb2


def get_dataset_id() -> str:
  """Retrieves and validates the BigQuery dataset ID from environment variables.

  Returns:
      The BigQuery dataset ID string.

  Raises:
      ValueError: If DATASET_ID environment variable is missing or contains hyphens.
  """
  dataset_id = os.environ.get("DATASET_ID")
  if not dataset_id:
    raise ValueError("DATASET_ID env variable is required")
  if "-" in dataset_id:
    raise ValueError("dataset_id must not contain hyphens (-)")
  return dataset_id


def get_team_github_repo() -> str:
  """Retrieves and validates the GitHub repository name from environment variables.

  Returns:
      The repository string in 'org/repo' format.

  Raises:
      ValueError: If TEAM_GITHUB_REPO environment variable is missing or not in
          'org/repo' format.
  """
  repo = os.environ.get("TEAM_GITHUB_REPO")
  if not repo:
    raise ValueError("TEAM_GITHUB_REPO environment variable is required")
  if not "/" in repo or len(repo.split("/")) != 2:
    raise ValueError("team_github_repo must be in format org/repo")
  return repo


def get_project_id() -> str | None:
  """Retrieves the GCP project ID from environment variables if set.

  Returns:
      The GCP project ID string, or None if not set.
  """
  # bq client selects the project id from default credentials if not provided.
  return os.environ.get("PROJECT_ID")


@functools.cache
def get_bq_client() -> bigquery.Client:
  """Returns a cached BigQuery client instance.

  Returns:
      A bigquery.Client instance.
  """
  return bigquery.Client()


@functools.cache
def get_validator() -> Validator:
  """Returns a cached Protovalidate Validator instance.

  Returns:
      A protovalidate.Validator instance.
  """
  return Validator()


@functions_framework.cloud_event
def subscribe(cloud_event: CloudEvent) -> None:
  """Triggered from a message on a Cloud Pub/Sub topic via Eventarc or Push.

  Args:
      cloud_event (cloudevents.http.CloudEvent): The CloudEvent payload.

  Raises:
      ValueError: If the event data is missing, base64 decoding fails, JSON payload is
          invalid, proto parsing fails, or validation fails.
      RuntimeError: If inserting rows into BigQuery encounters errors.
  """
  if "message" not in cloud_event.data or "data" not in cloud_event.data["message"]:
    raise ValueError("No data in event")

  github_repo = get_team_github_repo()
  repo_attr = cloud_event.data["message"].get("attributes", {}).get("repo")
  if repo_attr != github_repo:
    logging.warning(
      f"Discarding message: repo attribute '{repo_attr}' does not match TEAM_GITHUB_REPO '{github_repo}'"
    )
    return

  try:
    pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode(
      "utf-8"
    )
  except binascii.Error as e:
    raise ValueError(f"Failed to base64 decode pubsub message: {e}") from e
  except (UnicodeDecodeError, json.JSONDecodeError) as e:
    raise ValueError(f"Failed to decode or parse pubsub message: {e}") from e

  bm_result = benchmark_result_pb2.BenchmarkResult()
  try:
    json_format.Parse(pubsub_message, bm_result, ignore_unknown_fields=False)
  except json_format.ParseError as e:
    raise ValueError(f"Failed to parse BenchmarkResult proto: {e}") from e

  try:
    get_validator().validate(bm_result)
  except ValidationError as e:
    raise ValueError(f"Validation failed: {e}") from e

  dataset_id = get_dataset_id()
  if not dataset_id:
    # Infer dataset from github_repo if not provided
    raise ValueError("DATASET_ID env variable is required")

  bq_client = get_bq_client()
  project_id = get_project_id() or bq_client.project
  table_id = f"{project_id}.{dataset_id}.raw_benchmark_results"

  row_to_insert = {
    "run_timestamp": bm_result.run_timestamp.ToJsonString(),
    "benchmark_name": bm_result.benchmark_name,
    "environment_config_id": bm_result.environment_config_id,
    "workflow_type": workflow_type_pb2.WorkflowType.Name(bm_result.workflow_type),
    "github_repo": github_repo,
    "branch": bm_result.branch,
    "payload": pubsub_message,
  }

  errors = bq_client.insert_rows_json(table_id, [row_to_insert])
  if errors:
    raise RuntimeError(f"Encountered errors while inserting rows: {errors}")
  else:
    logging.info(f"Successfully inserted row into {table_id}")


if __name__ == "__main__":
  from functions_framework._cli import _cli

  _cli(
    args=[
      "--target=subscribe",
      "--source=" + __file__,
      "--host=0.0.0.0",
      "--port=" + os.environ.get("PORT", "8080"),
    ]
  )
