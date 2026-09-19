from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.models.audit_event import AuditEvent


def save_audit_event(
    audit_event: AuditEvent,
    table_name: str,
    dynamodb_resource: Any = None,
) -> bool:
    dynamodb = dynamodb_resource or boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    item = audit_event.model_dump(mode="json")

    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(event_id)",
        )

        return True

    except ClientError as error:
        error_code = error.response["Error"]["Code"]

        if error_code == "ConditionalCheckFailedException":
            return False

        raise