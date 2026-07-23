import base64
import json
import logging
import os
import functions_framework
from google.cloud import bigquery
from google.protobuf import json_format
from protovalidate import Validator

from bap_proto import benchmark_result_pb2
from bap_proto.common import workflow_type_pb2

# Initialize clients globally for reuse
client = None
validator = None


def get_dataset_id():
  dataset_id = os.environ.get("DATASET_ID")
  if dataset_id and "-" in dataset_id:
    raise ValueError("dataset_id must not contain hyphens (-)")
  return dataset_id


def get_team_github_repo():
  repo = os.environ.get("TEAM_GITHUB_REPO")
  if not repo:
    raise ValueError("TEAM_GITHUB_REPO environment variable is required")
  if not "/" in repo or len(repo.split("/")) != 2:
    raise ValueError("team_github_repo must be in format org/repo")
  return repo


def get_project_id():
  # bq client selects the project id from default credentials if not provided.
  return os.environ.get("PROJECT_ID")


def get_bq_client():
  global client
  if client is None:
    client = bigquery.Client()
  return client


def get_validator():
  global validator
  if validator is None:
    validator = Validator()
  return validator


@functions_framework.cloud_event
def subscribe(cloud_event):
  """Triggered from a message on a Cloud Pub/Sub topic via Eventarc or Push.
  Args:
       cloud_event (cloudevents.http.CloudEvent): The CloudEvent payload.
  """
  if "message" not in cloud_event.data or "data" not in cloud_event.data["message"]:
    logging.error("No data in event")
    return

  try:
    pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode(
      "utf-8"
    )
    payload_dict = json.loads(pubsub_message)
  except Exception as e:
    logging.error(f"Failed to decode or parse pubsub message: {e}")
    return

  try:
    bm_result = benchmark_result_pb2.BenchmarkResult()
    json_format.Parse(pubsub_message, bm_result, ignore_unknown_fields=False)
  except Exception as e:
    logging.error(f"Failed to parse BenchmarkResult proto: {e}")
    return

  try:
    get_validator().validate(bm_result)
  except Exception as e:
    logging.error(f"Validation failed: {e}")
    return

  github_repo = get_team_github_repo()
  dataset_id = get_dataset_id()
  if not dataset_id:
    # Infer dataset from github_repo if not provided
    dataset_id = github_repo.split("/")[0].replace("-", "_")

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

  try:
    errors = bq_client.insert_rows_json(table_id, [row_to_insert])
    if errors:
      logging.error(f"Encountered errors while inserting rows: {errors}")
    else:
      logging.info(f"Successfully inserted row into {table_id}")
  except Exception as e:
    logging.error(f"Failed to insert into BigQuery: {e}")
    raise e


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
