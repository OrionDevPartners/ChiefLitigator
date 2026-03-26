"""Provision DynamoDB tables for ChiefLitigator.

Tables:
  - ChiefLitigator_Sessions: User session data (TTL-enabled)
  - ChiefLitigator_Cases: Case state snapshots
  - ChiefLitigator_GalvanizerLogs: Galvanizer debate round transcripts

Usage:
  python infrastructure/provision_dynamodb.py

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import os
import boto3

REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

client = boto3.client("dynamodb", region_name=REGION)

TABLES = [
    {
        "TableName": os.getenv("DYNAMO_SESSIONS_TABLE", "ChiefLitigator_Sessions"),
        "KeySchema": [
            {"AttributeName": "session_id", "KeyType": "HASH"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "session_id", "AttributeType": "S"},
            {"AttributeName": "user_id", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "user_id-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "Tags": [
            {"Key": "Project", "Value": "ChiefLitigator"},
            {"Key": "Environment", "Value": os.getenv("ENVIRONMENT", "production")},
        ],
        "TTL": {"AttributeName": "expires_at", "Enabled": True},
    },
    {
        "TableName": os.getenv("DYNAMO_CASES_TABLE", "ChiefLitigator_Cases"),
        "KeySchema": [
            {"AttributeName": "case_id", "KeyType": "HASH"},
            {"AttributeName": "version", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "case_id", "AttributeType": "S"},
            {"AttributeName": "version", "AttributeType": "N"},
            {"AttributeName": "user_id", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "user_id-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "Tags": [
            {"Key": "Project", "Value": "ChiefLitigator"},
            {"Key": "Environment", "Value": os.getenv("ENVIRONMENT", "production")},
        ],
    },
    {
        "TableName": os.getenv("DYNAMO_GALVANIZER_TABLE", "ChiefLitigator_GalvanizerLogs"),
        "KeySchema": [
            {"AttributeName": "case_id", "KeyType": "HASH"},
            {"AttributeName": "round_id", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "case_id", "AttributeType": "S"},
            {"AttributeName": "round_id", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "Tags": [
            {"Key": "Project", "Value": "ChiefLitigator"},
            {"Key": "Environment", "Value": os.getenv("ENVIRONMENT", "production")},
        ],
    },
]


def provision() -> None:
    """Create all DynamoDB tables."""
    existing = client.list_tables()["TableNames"]

    for table_spec in TABLES:
        name = table_spec["TableName"]
        if name in existing:
            print(f"  [SKIP] {name} already exists")
            continue

        ttl_config = table_spec.pop("TTL", None)

        create_params = {k: v for k, v in table_spec.items()}
        client.create_table(**create_params)
        print(f"  [CREATE] {name}")

        waiter = client.get_waiter("table_exists")
        waiter.wait(TableName=name)

        if ttl_config:
            client.update_time_to_live(
                TableName=name,
                TimeToLiveSpecification={
                    "Enabled": ttl_config["Enabled"],
                    "AttributeName": ttl_config["AttributeName"],
                },
            )
            print(f"  [TTL] {name} → {ttl_config['AttributeName']}")

    print("DynamoDB provisioning complete.")


if __name__ == "__main__":
    provision()
