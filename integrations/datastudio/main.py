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
  dataset_id = os.environ.get("DATASET_ID")
  if not dataset_id:
    raise ValueError("DATASET_ID env variable is required")
  if "-" in dataset_id:
    raise ValueError("dataset_id must not contain hyphens (-)")
  return dataset_id


def get_team_github_repo() -> str:
  repo = os.environ.get("TEAM_GITHUB_REPO")
  if not repo:
    raise ValueError("TEAM_GITHUB_REPO environment variable is required")
  if not "/" in repo or len(repo.split("/")) != 2:
    raise ValueError("team_github_repo must be in format org/repo")
  return repo


def get_project_id() -> str | None:
  # bq client selects the project id from default credentials if not provided.
  return os.environ.get("PROJECT_ID")


@functools.cache
def get_bq_client() -> bigquery.Client:
  return bigquery.Client()


@functools.cache
def get_validator() -> Validator:
  return Validator()


@functions_framework.cloud_event
def subscribe(cloud_event: CloudEvent) -> None:
  """Triggered from a message on a Cloud Pub/Sub topic via Eventarc or Push.
  Args:
       cloud_event (cloudevents.http.CloudEvent): The CloudEvent payload.
  """
  if "message" not in cloud_event.data or "data" not in cloud_event.data["message"]:
    raise ValueError("No data in event")

  github_repo = get_team_github_repo()
  repo_attr = cloud_event.data["message"].get("attributes", {}).get("repo")
  if repo_attr != github_repo:
    logging.info(
      f"Discarding message: repo attribute '{repo_attr}' does not match TEAM_GITHUB_REPO '{github_repo}'"
    )
    return

  try:
    pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode(
      "utf-8"
    )
    payload_dict = json.loads(pubsub_message)
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
