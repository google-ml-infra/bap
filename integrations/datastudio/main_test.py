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

"""Tests for the Data Studio integration Cloud Function."""

import base64
import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

from integrations.datastudio import main


@pytest.fixture(autouse=True)
def set_team_github_repo_env(monkeypatch):
  """Sets default TEAM_GITHUB_REPO environment variable for tests."""
  monkeypatch.setenv("TEAM_GITHUB_REPO", "org/repo")


def test_get_dataset_id(monkeypatch):
  """Tests successfully getting dataset ID from environment."""
  monkeypatch.setenv("DATASET_ID", "my_dataset")
  assert main.get_dataset_id() == "my_dataset"


def test_get_dataset_id_with_hyphen(monkeypatch):
  """Tests that dataset ID containing hyphens raises ValueError."""
  monkeypatch.setenv("DATASET_ID", "my-dataset")
  with pytest.raises(ValueError, match="dataset_id must not contain hyphens"):
    main.get_dataset_id()


def test_get_dataset_id_missing(monkeypatch):
  """Tests that missing dataset ID raises ValueError."""
  monkeypatch.delenv("DATASET_ID", raising=False)
  with pytest.raises(ValueError, match="DATASET_ID env variable is required"):
    main.get_dataset_id()


def test_get_team_github_repo(monkeypatch):
  """Tests successfully getting GitHub repo from environment."""
  monkeypatch.setenv("TEAM_GITHUB_REPO", "org/repo")
  assert main.get_team_github_repo() == "org/repo"


def test_get_team_github_repo_missing(monkeypatch):
  """Tests that missing TEAM_GITHUB_REPO raises ValueError."""
  monkeypatch.delenv("TEAM_GITHUB_REPO", raising=False)
  with pytest.raises(
    ValueError, match="TEAM_GITHUB_REPO environment variable is required"
  ):
    main.get_team_github_repo()


def test_get_team_github_repo_invalid_format_1(monkeypatch):
  """Tests that TEAM_GITHUB_REPO without slash raises ValueError."""
  monkeypatch.setenv("TEAM_GITHUB_REPO", "org_repo")
  with pytest.raises(ValueError, match="team_github_repo must be in format org/repo"):
    main.get_team_github_repo()


def test_get_team_github_repo_invalid_format_2(monkeypatch):
  """Tests that TEAM_GITHUB_REPO with extra slashes raises ValueError."""
  monkeypatch.setenv("TEAM_GITHUB_REPO", "org/repo/extra")
  with pytest.raises(ValueError, match="team_github_repo must be in format org/repo"):
    main.get_team_github_repo()


def test_get_project_id(monkeypatch):
  """Tests retrieving project ID from environment."""
  monkeypatch.setenv("PROJECT_ID", "my-project")
  assert main.get_project_id() == "my-project"


@patch("integrations.datastudio.main.bigquery.Client")
def test_get_bq_client(mock_bq_client):
  """Tests BigQuery client creation and caching."""
  main.client = None
  client = main.get_bq_client()
  mock_bq_client.assert_called_once()
  assert client == mock_bq_client.return_value

  # Test caching
  client2 = main.get_bq_client()
  assert client2 == client
  mock_bq_client.assert_called_once()  # Still only called once


@patch("integrations.datastudio.main.Validator")
def test_get_validator(mock_validator):
  """Tests validator creation and caching."""
  main.validator = None
  validator = main.get_validator()
  mock_validator.assert_called_once()
  assert validator == mock_validator.return_value

  # Test caching
  validator2 = main.get_validator()
  assert validator2 == validator
  mock_validator.assert_called_once()


def test_subscribe_missing_data():
  """Tests subscribe function when event data is missing."""
  cloud_event = MagicMock()
  cloud_event.data = {}
  with pytest.raises(ValueError, match="No data in event"):
    main.subscribe(cloud_event)


def test_subscribe_invalid_base64():
  """Tests subscribe function with invalid base64 payload."""
  cloud_event = MagicMock()
  cloud_event.data = {
    "message": {"data": "invalid-base64-!@#", "attributes": {"repo": "org/repo"}}
  }
  with pytest.raises(ValueError, match="Failed to base64 decode pubsub message"):
    main.subscribe(cloud_event)


def test_subscribe_invalid_json():
  """Tests subscribe function with invalid JSON payload."""
  invalid_json_b64 = base64.b64encode(b"not json").decode("utf-8")
  cloud_event = MagicMock()
  cloud_event.data = {
    "message": {"data": invalid_json_b64, "attributes": {"repo": "org/repo"}}
  }
  with pytest.raises(ValueError, match="Failed to parse BenchmarkResult proto"):
    main.subscribe(cloud_event)


@patch("integrations.datastudio.main.json_format.Parse")
def test_subscribe_proto_parse_error(mock_parse):
  """Tests subscribe function when BenchmarkResult proto parsing fails."""
  valid_json_b64 = base64.b64encode(b'{"some": "data"}').decode("utf-8")
  cloud_event = MagicMock()
  cloud_event.data = {
    "message": {"data": valid_json_b64, "attributes": {"repo": "org/repo"}}
  }
  mock_parse.side_effect = main.json_format.ParseError("parse error")

  with pytest.raises(ValueError, match="Failed to parse BenchmarkResult proto"):
    main.subscribe(cloud_event)


@patch("integrations.datastudio.main.json_format.Parse")
@patch("integrations.datastudio.main.get_validator")
def test_subscribe_validation_error(mock_get_validator, mock_parse):
  """Tests subscribe function when BenchmarkResult validation fails."""
  valid_json_b64 = base64.b64encode(b'{"some": "data"}').decode("utf-8")
  cloud_event = MagicMock()
  cloud_event.data = {
    "message": {"data": valid_json_b64, "attributes": {"repo": "org/repo"}}
  }

  mock_validator = MagicMock()
  mock_validator.validate.side_effect = main.ValidationError(
    msg="validation error", violations=[]
  )
  mock_get_validator.return_value = mock_validator

  with pytest.raises(ValueError, match="Validation failed"):
    main.subscribe(cloud_event)


@patch("integrations.datastudio.main.logging")
@patch("integrations.datastudio.main.json_format.Parse")
@patch("integrations.datastudio.main.get_validator")
@patch("integrations.datastudio.main.get_team_github_repo")
@patch("integrations.datastudio.main.get_dataset_id")
@patch("integrations.datastudio.main.get_project_id")
@patch("integrations.datastudio.main.get_bq_client")
@patch("integrations.datastudio.main.benchmark_result_pb2.BenchmarkResult")
def test_subscribe_success(
  mock_benchmark_result,
  mock_get_bq_client,
  mock_get_project_id,
  mock_get_dataset_id,
  mock_get_team_github_repo,
  mock_get_validator,
  mock_parse,
  mock_logging,
):
  """Tests successful processing and insertion into BigQuery."""
  payload_str = '{"some": "data"}'
  valid_json_b64 = base64.b64encode(payload_str.encode("utf-8")).decode("utf-8")
  cloud_event = MagicMock()
  cloud_event.data = {
    "message": {"data": valid_json_b64, "attributes": {"repo": "my-org/my-repo"}}
  }

  mock_get_team_github_repo.return_value = "my-org/my-repo"
  mock_get_dataset_id.return_value = "my_dataset"
  mock_get_project_id.return_value = "my_project"

  mock_bq_client = MagicMock()
  mock_bq_client.insert_rows_json.return_value = []
  mock_get_bq_client.return_value = mock_bq_client

  mock_bm_result = MagicMock()
  mock_bm_result.run_timestamp.ToJsonString.return_value = "2023-01-01T00:00:00Z"
  mock_bm_result.benchmark_name = "test_bench"
  mock_bm_result.environment_config_id = "env-123"
  mock_bm_result.workflow_type = 1
  mock_bm_result.branch = "main"

  with patch(
    "integrations.datastudio.main.workflow_type_pb2.WorkflowType.Name",
    return_value="CONTINUOUS",
  ):
    mock_benchmark_result.return_value = mock_bm_result

    main.subscribe(cloud_event)

    mock_bq_client.insert_rows_json.assert_called_once()
    table_id, rows = mock_bq_client.insert_rows_json.call_args[0]

    assert table_id == "my_project.my_dataset.raw_benchmark_results"
    assert len(rows) == 1
    assert rows[0]["run_timestamp"] == "2023-01-01T00:00:00Z"
    assert rows[0]["benchmark_name"] == "test_bench"
    assert rows[0]["github_repo"] == "my-org/my-repo"
    assert rows[0]["workflow_type"] == "CONTINUOUS"
    assert rows[0]["payload"] == payload_str

    mock_logging.info.assert_called_once()
    assert "Successfully inserted row" in mock_logging.info.call_args[0][0]


@patch("integrations.datastudio.main.json_format.Parse")
@patch("integrations.datastudio.main.get_validator")
@patch("integrations.datastudio.main.get_team_github_repo")
@patch("integrations.datastudio.main.get_bq_client")
@patch("integrations.datastudio.main.benchmark_result_pb2.BenchmarkResult")
def test_subscribe_bq_insert_error(
  mock_benchmark_result,
  mock_get_bq_client,
  mock_get_team_github_repo,
  mock_get_validator,
  mock_parse,
):
  """Tests subscribe function handling BigQuery insertion row errors."""
  payload_str = '{"some": "data"}'
  valid_json_b64 = base64.b64encode(payload_str.encode("utf-8")).decode("utf-8")
  cloud_event = MagicMock()
  cloud_event.data = {
    "message": {"data": valid_json_b64, "attributes": {"repo": "org/repo"}}
  }

  mock_get_team_github_repo.return_value = "org/repo"

  mock_bq_client = MagicMock()
  mock_bq_client.insert_rows_json.return_value = [
    {"index": 0, "errors": [{"reason": "invalid"}]}
  ]
  mock_get_bq_client.return_value = mock_bq_client

  with patch("integrations.datastudio.main.get_project_id", return_value="proj"):
    with patch("integrations.datastudio.main.get_dataset_id", return_value="ds"):
      with patch(
        "integrations.datastudio.main.workflow_type_pb2.WorkflowType.Name",
        return_value="PR",
      ):
        with pytest.raises(
          RuntimeError, match="Encountered errors while inserting rows"
        ):
          main.subscribe(cloud_event)


@patch("integrations.datastudio.main.json_format.Parse")
@patch("integrations.datastudio.main.get_validator")
@patch("integrations.datastudio.main.get_team_github_repo")
@patch("integrations.datastudio.main.get_bq_client")
@patch("integrations.datastudio.main.benchmark_result_pb2.BenchmarkResult")
def test_subscribe_bq_insert_exception(
  mock_benchmark_result,
  mock_get_bq_client,
  mock_get_team_github_repo,
  mock_get_validator,
  mock_parse,
):
  """Tests subscribe function handling BigQuery insertion exception."""
  payload_str = '{"some": "data"}'
  valid_json_b64 = base64.b64encode(payload_str.encode("utf-8")).decode("utf-8")
  cloud_event = MagicMock()
  cloud_event.data = {
    "message": {"data": valid_json_b64, "attributes": {"repo": "org/repo"}}
  }

  mock_get_team_github_repo.return_value = "org/repo"

  mock_bq_client = MagicMock()
  mock_bq_client.insert_rows_json.side_effect = Exception("bq error")
  mock_get_bq_client.return_value = mock_bq_client

  with patch("integrations.datastudio.main.get_project_id", return_value="proj"):
    with patch("integrations.datastudio.main.get_dataset_id", return_value="ds"):
      with patch(
        "integrations.datastudio.main.workflow_type_pb2.WorkflowType.Name",
        return_value="PR",
      ):
        with pytest.raises(Exception, match="bq error"):
          main.subscribe(cloud_event)


@patch("integrations.datastudio.main.logging")
def test_subscribe_discard_different_repo(mock_logging):
  """Tests discarding messages when repo attribute does not match target repo."""
  payload_str = '{"some": "data"}'
  valid_json_b64 = base64.b64encode(payload_str.encode("utf-8")).decode("utf-8")
  cloud_event = MagicMock()
  cloud_event.data = {
    "message": {
      "data": valid_json_b64,
      "attributes": {"repo": "different/repo"},
    }
  }

  main.subscribe(cloud_event)
  mock_logging.warning.assert_called_once()
  assert "Discarding message" in mock_logging.warning.call_args[0][0]


@patch("integrations.datastudio.main.logging")
def test_subscribe_discard_missing_repo(mock_logging):
  """Tests discarding messages when repo attribute is missing."""
  payload_str = '{"some": "data"}'
  valid_json_b64 = base64.b64encode(payload_str.encode("utf-8")).decode("utf-8")
  cloud_event = MagicMock()
  cloud_event.data = {"message": {"data": valid_json_b64}}

  main.subscribe(cloud_event)
  mock_logging.warning.assert_called_once()
  assert "Discarding message" in mock_logging.warning.call_args[0][0]


if __name__ == "__main__":
  sys.exit(pytest.main(sys.argv))
