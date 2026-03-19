"""
Ciphergy Pipeline — AWS Services Connector

Provides unified access to AWS services: S3, DynamoDB, SES, CloudWatch,
and Bedrock delegation. Uses boto3 for all AWS API calls.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ciphergy.connectors.base import BaseConnector, ConnectorConfig

logger = logging.getLogger(__name__)


class AWSConnector(BaseConnector):
    """
    AWS connector for Ciphergy Pipeline.

    Provides S3 file operations, DynamoDB CRUD, SES email notifications,
    CloudWatch logging/metrics, and Bedrock model invocation delegation.
    All operations use boto3 clients created on connect().
    """

    CONNECTOR_NAME = "aws"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._region: str = config.extra.get("region", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        self._account_id: str = config.extra.get("account_id", "")
        self._clients: Dict[str, Any] = {}
        self._session: Any = None

    # ── Connection lifecycle ────────────────────────────────────────

    def connect(self) -> bool:
        """
        Initialize boto3 session and verify AWS credentials.

        Returns:
            True if credentials are valid and STS caller identity succeeds.
        """
        try:
            import boto3
        except ImportError:
            self._logger.error("boto3 not installed. Run: pip install boto3")
            return False

        try:
            self._session = boto3.Session(region_name=self._region)
            sts = self._session.client("sts")
            identity = sts.get_caller_identity()
            self._account_id = identity.get("Account", "")
            self._logger.info(
                "Connected to AWS account %s as %s",
                self._account_id,
                identity.get("Arn", ""),
            )
            self._connected = True
            return True
        except Exception as exc:
            self._logger.error("Failed to connect to AWS: %s", exc)
            return False

    def disconnect(self) -> None:
        """Clear boto3 clients and mark disconnected."""
        self._clients.clear()
        self._session = None
        self._connected = False
        self._logger.info("Disconnected from AWS")

    def health_check(self) -> bool:
        """Verify AWS credentials are still valid."""
        try:
            sts = self._get_client("sts")
            sts.get_caller_identity()
            return True
        except Exception:
            return False

    # ── Core interface ──────────────────────────────────────────────

    def fetch(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Fetch data from an AWS service.

        Args:
            query: Service-qualified query in the form "service:operation"
                   (e.g., "s3:list", "dynamodb:get", "cloudwatch:query").
            **kwargs: Service-specific parameters.

        Returns:
            Dict with "data", "status", and "connector" keys.
        """
        service, _, operation = query.partition(":")
        handlers = {
            "s3": self._s3_fetch,
            "dynamodb": self._dynamodb_fetch,
            "cloudwatch": self._cloudwatch_fetch,
        }

        handler = handlers.get(service.lower())
        if not handler:
            return {"data": None, "status": "error", "connector": "aws", "error": f"Unknown service: {service}"}

        data = self._with_retry(f"AWS {service}:{operation}", handler, operation, **kwargs)
        return {"data": data, "status": "ok", "connector": "aws"}

    def push(self, data: Dict[str, Any], **kwargs: Any) -> bool:
        """
        Push data to an AWS service.

        Args:
            data: Must contain "service" and "operation" keys.
            **kwargs: Additional parameters.

        Returns:
            True if successful.
        """
        service = data.get("service", "")
        operation = data.get("operation", "")
        payload = data.get("payload", {})

        handlers = {
            "s3": self._s3_push,
            "dynamodb": self._dynamodb_push,
            "ses": self._ses_push,
            "cloudwatch": self._cloudwatch_push,
        }

        handler = handlers.get(service.lower())
        if not handler:
            self._logger.error("Unknown AWS service: %s", service)
            return False

        self._with_retry(f"AWS push {service}:{operation}", handler, operation, payload, **kwargs)
        return True

    # ── S3 operations ───────────────────────────────────────────────

    def s3_upload(self, bucket: str, key: str, body: bytes, content_type: str = "application/octet-stream") -> bool:
        """
        Upload an object to S3.

        Args:
            bucket: S3 bucket name.
            key: Object key (path).
            body: File content as bytes.
            content_type: MIME type of the content.

        Returns:
            True if uploaded successfully.
        """
        s3 = self._get_client("s3")
        self._with_retry(
            f"S3 upload {bucket}/{key}",
            s3.put_object,
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )
        self._logger.info("Uploaded to s3://%s/%s", bucket, key)
        return True

    def s3_download(self, bucket: str, key: str) -> bytes:
        """
        Download an object from S3.

        Args:
            bucket: S3 bucket name.
            key: Object key.

        Returns:
            The file content as bytes.
        """
        s3 = self._get_client("s3")
        response = self._with_retry(f"S3 download {bucket}/{key}", s3.get_object, Bucket=bucket, Key=key)
        return response["Body"].read()

    def s3_list(self, bucket: str, prefix: str = "", max_keys: int = 1000) -> List[Dict[str, Any]]:
        """
        List objects in an S3 bucket.

        Args:
            bucket: S3 bucket name.
            prefix: Key prefix filter.
            max_keys: Maximum number of keys to return.

        Returns:
            List of object metadata dicts (Key, Size, LastModified).
        """
        s3 = self._get_client("s3")
        response = self._with_retry(
            f"S3 list {bucket}/{prefix}",
            s3.list_objects_v2,
            Bucket=bucket,
            Prefix=prefix,
            MaxKeys=max_keys,
        )
        contents = response.get("Contents", [])
        return [
            {
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
            }
            for obj in contents
        ]

    def s3_delete(self, bucket: str, key: str) -> bool:
        """
        Delete an object from S3.

        Args:
            bucket: S3 bucket name.
            key: Object key.

        Returns:
            True if deleted.
        """
        s3 = self._get_client("s3")
        self._with_retry(f"S3 delete {bucket}/{key}", s3.delete_object, Bucket=bucket, Key=key)
        return True

    # ── DynamoDB operations ─────────────────────────────────────────

    def dynamodb_put(self, table: str, item: Dict[str, Any]) -> bool:
        """
        Put an item into a DynamoDB table.

        Args:
            table: Table name.
            item: Item dict (keys are attribute names, values are native Python types).

        Returns:
            True if successful.
        """
        dynamodb = self._get_client("dynamodb", resource=True)
        tbl = dynamodb.Table(table)
        self._with_retry(f"DynamoDB put {table}", tbl.put_item, Item=item)
        return True

    def dynamodb_get(self, table: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get an item from a DynamoDB table.

        Args:
            table: Table name.
            key: Primary key dict.

        Returns:
            The item dict, or None if not found.
        """
        dynamodb = self._get_client("dynamodb", resource=True)
        tbl = dynamodb.Table(table)
        response = self._with_retry(f"DynamoDB get {table}", tbl.get_item, Key=key)
        return response.get("Item")

    def dynamodb_query(
        self,
        table: str,
        key_condition: str,
        expression_values: Dict[str, Any],
        index_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query a DynamoDB table.

        Args:
            table: Table name.
            key_condition: KeyConditionExpression string.
            expression_values: ExpressionAttributeValues dict.
            index_name: Optional GSI name.
            limit: Maximum items to return.

        Returns:
            List of matching items.
        """
        dynamodb = self._get_client("dynamodb", resource=True)
        tbl = dynamodb.Table(table)

        query_kwargs: Dict[str, Any] = {
            "KeyConditionExpression": key_condition,
            "ExpressionAttributeValues": expression_values,
            "Limit": limit,
        }
        if index_name:
            query_kwargs["IndexName"] = index_name

        response = self._with_retry(f"DynamoDB query {table}", tbl.query, **query_kwargs)
        return response.get("Items", [])

    def dynamodb_delete(self, table: str, key: Dict[str, Any]) -> bool:
        """
        Delete an item from a DynamoDB table.

        Args:
            table: Table name.
            key: Primary key dict.

        Returns:
            True if deleted.
        """
        dynamodb = self._get_client("dynamodb", resource=True)
        tbl = dynamodb.Table(table)
        self._with_retry(f"DynamoDB delete {table}", tbl.delete_item, Key=key)
        return True

    def dynamodb_update(
        self,
        table: str,
        key: Dict[str, Any],
        update_expression: str,
        expression_values: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an item in a DynamoDB table.

        Args:
            table: Table name.
            key: Primary key dict.
            update_expression: UpdateExpression string (e.g., "SET #s = :val").
            expression_values: ExpressionAttributeValues dict.

        Returns:
            The updated attributes.
        """
        dynamodb = self._get_client("dynamodb", resource=True)
        tbl = dynamodb.Table(table)
        response = self._with_retry(
            f"DynamoDB update {table}",
            tbl.update_item,
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes", {})

    # ── SES operations ──────────────────────────────────────────────

    def ses_send_email(
        self,
        to: List[str],
        subject: str,
        body_text: str = "",
        body_html: str = "",
        from_addr: Optional[str] = None,
        reply_to: Optional[List[str]] = None,
    ) -> str:
        """
        Send an email via SES.

        Args:
            to: List of recipient email addresses.
            subject: Email subject.
            body_text: Plain text body.
            body_html: HTML body (optional).
            from_addr: Sender address (defaults to config or env).
            reply_to: Reply-to addresses.

        Returns:
            The SES MessageId.
        """
        ses = self._get_client("ses")
        sender = from_addr or self.config.extra.get(
            "ses_from", os.environ.get("SES_FROM_EMAIL", "noreply@ciphergy.local")
        )

        body: Dict[str, Any] = {}
        if body_text:
            body["Text"] = {"Data": body_text, "Charset": "UTF-8"}
        if body_html:
            body["Html"] = {"Data": body_html, "Charset": "UTF-8"}
        if not body:
            body["Text"] = {"Data": "(no body)", "Charset": "UTF-8"}

        kwargs: Dict[str, Any] = {
            "Source": sender,
            "Destination": {"ToAddresses": to},
            "Message": {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": body,
            },
        }
        if reply_to:
            kwargs["ReplyToAddresses"] = reply_to

        response = self._with_retry("SES send email", ses.send_email, **kwargs)
        message_id = response.get("MessageId", "")
        self._logger.info("Sent email to %s (MessageId: %s)", to, message_id)
        return message_id

    # ── CloudWatch operations ───────────────────────────────────────

    def cloudwatch_put_metric(
        self,
        namespace: str,
        metric_name: str,
        value: float,
        unit: str = "None",
        dimensions: Optional[List[Dict[str, str]]] = None,
    ) -> bool:
        """
        Publish a metric to CloudWatch.

        Args:
            namespace: Metric namespace (e.g., "Ciphergy/Pipeline").
            metric_name: Metric name.
            value: Metric value.
            unit: Unit type (e.g., "Count", "Seconds", "None").
            dimensions: Optional list of {"Name": ..., "Value": ...} dicts.

        Returns:
            True if published.
        """
        cw = self._get_client("cloudwatch")
        metric_data: Dict[str, Any] = {
            "MetricName": metric_name,
            "Value": value,
            "Unit": unit,
            "Timestamp": datetime.now(timezone.utc),
        }
        if dimensions:
            metric_data["Dimensions"] = dimensions

        self._with_retry(
            f"CloudWatch put metric {metric_name}",
            cw.put_metric_data,
            Namespace=namespace,
            MetricData=[metric_data],
        )
        return True

    def cloudwatch_log(
        self, log_group: str, log_stream: str, message: str, sequence_token: Optional[str] = None
    ) -> Optional[str]:
        """
        Write a log event to CloudWatch Logs.

        Args:
            log_group: Log group name.
            log_stream: Log stream name.
            message: Log message.
            sequence_token: Sequence token for the stream (None for first write).

        Returns:
            The next sequence token, or None on failure.
        """
        logs = self._get_client("logs")

        # Ensure log group and stream exist
        try:
            logs.create_log_group(logGroupName=log_group)
        except Exception:
            pass  # Already exists
        try:
            logs.create_log_stream(logGroupName=log_group, logStreamName=log_stream)
        except Exception:
            pass  # Already exists

        kwargs: Dict[str, Any] = {
            "logGroupName": log_group,
            "logStreamName": log_stream,
            "logEvents": [
                {
                    "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "message": message,
                }
            ],
        }
        if sequence_token:
            kwargs["sequenceToken"] = sequence_token

        try:
            response = self._with_retry("CloudWatch log", logs.put_log_events, **kwargs)
            return response.get("nextSequenceToken")
        except Exception as exc:
            self._logger.warning("CloudWatch log failed: %s", exc)
            return None

    def cloudwatch_get_metrics(
        self,
        namespace: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        period: int = 300,
        stat: str = "Average",
        dimensions: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get metric statistics from CloudWatch.

        Args:
            namespace: Metric namespace.
            metric_name: Metric name.
            start_time: Start of the time range.
            end_time: End of the time range.
            period: Aggregation period in seconds.
            stat: Statistic type ("Average", "Sum", "Maximum", "Minimum", "SampleCount").
            dimensions: Optional dimension filters.

        Returns:
            List of datapoint dicts.
        """
        cw = self._get_client("cloudwatch")

        kwargs: Dict[str, Any] = {
            "Namespace": namespace,
            "MetricName": metric_name,
            "StartTime": start_time,
            "EndTime": end_time,
            "Period": period,
            "Statistics": [stat],
        }
        if dimensions:
            kwargs["Dimensions"] = dimensions

        response = self._with_retry("CloudWatch get metrics", cw.get_metric_statistics, **kwargs)
        return response.get("Datapoints", [])

    # ── Bedrock delegation ──────────────────────────────────────────

    def bedrock_invoke(
        self, model_id: str, prompt: str, max_tokens: int = 4096, temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Invoke a Bedrock model. Delegates to the model-specific invocation format.

        Args:
            model_id: Bedrock model ID or inference profile ARN.
            prompt: The prompt text.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Returns:
            Dict with "text" (generated text) and "usage" (token counts).
        """
        bedrock = self._get_client("bedrock-runtime")

        # Build request based on model family
        if "anthropic" in model_id or "claude" in model_id:
            body = json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [{"role": "user", "content": prompt}],
                }
            )
            accept = "application/json"
        elif "mistral" in model_id:
            body = json.dumps(
                {
                    "prompt": f"<s>[INST] {prompt} [/INST]",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            )
            accept = "application/json"
        elif "amazon" in model_id or "nova" in model_id:
            body = json.dumps(
                {
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": max_tokens,
                        "temperature": temperature,
                    },
                }
            )
            accept = "application/json"
        else:
            # Generic fallback
            body = json.dumps(
                {
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            )
            accept = "application/json"

        response = self._with_retry(
            f"Bedrock invoke {model_id}",
            bedrock.invoke_model,
            modelId=model_id,
            body=body,
            accept=accept,
            contentType="application/json",
        )

        response_body = json.loads(response["body"].read())

        # Parse response based on model family
        text = ""
        usage: Dict[str, Any] = {}

        if "anthropic" in model_id or "claude" in model_id:
            content = response_body.get("content", [])
            text = content[0].get("text", "") if content else ""
            usage = response_body.get("usage", {})
        elif "mistral" in model_id:
            outputs = response_body.get("outputs", [])
            text = outputs[0].get("text", "") if outputs else ""
        elif "amazon" in model_id or "nova" in model_id:
            results = response_body.get("results", [])
            text = results[0].get("outputText", "") if results else ""
        else:
            text = response_body.get("generation", response_body.get("text", str(response_body)))

        return {"text": text, "usage": usage, "model_id": model_id}

    # ── Private helpers ─────────────────────────────────────────────

    def _get_client(self, service: str, resource: bool = False) -> Any:
        """
        Get or create a boto3 client/resource for a service.

        Args:
            service: AWS service name.
            resource: If True, return a boto3 resource instead of client.

        Returns:
            The boto3 client or resource.
        """
        cache_key = f"{service}:{'resource' if resource else 'client'}"
        if cache_key not in self._clients:
            if self._session is None:
                import boto3

                self._session = boto3.Session(region_name=self._region)

            if resource:
                self._clients[cache_key] = self._session.resource(service, region_name=self._region)
            else:
                self._clients[cache_key] = self._session.client(service, region_name=self._region)

        return self._clients[cache_key]

    def _s3_fetch(self, operation: str, **kwargs: Any) -> Any:
        """Route S3 fetch operations."""
        if operation == "list":
            return self.s3_list(kwargs["bucket"], kwargs.get("prefix", ""))
        elif operation == "download":
            content = self.s3_download(kwargs["bucket"], kwargs["key"])
            return {"content": content.decode("utf-8", errors="replace"), "size": len(content)}
        else:
            raise ValueError(f"Unknown S3 fetch operation: {operation}")

    def _s3_push(self, operation: str, payload: Dict[str, Any], **kwargs: Any) -> None:
        """Route S3 push operations."""
        if operation == "upload":
            body = payload.get("body", b"")
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.s3_upload(
                payload["bucket"], payload["key"], body, payload.get("content_type", "application/octet-stream")
            )
        elif operation == "delete":
            self.s3_delete(payload["bucket"], payload["key"])
        else:
            raise ValueError(f"Unknown S3 push operation: {operation}")

    def _dynamodb_fetch(self, operation: str, **kwargs: Any) -> Any:
        """Route DynamoDB fetch operations."""
        if operation == "get":
            return self.dynamodb_get(kwargs["table"], kwargs["key"])
        elif operation == "query":
            return self.dynamodb_query(
                kwargs["table"],
                kwargs["key_condition"],
                kwargs["expression_values"],
                kwargs.get("index_name"),
                kwargs.get("limit", 100),
            )
        else:
            raise ValueError(f"Unknown DynamoDB fetch operation: {operation}")

    def _dynamodb_push(self, operation: str, payload: Dict[str, Any], **kwargs: Any) -> None:
        """Route DynamoDB push operations."""
        if operation == "put":
            self.dynamodb_put(payload["table"], payload["item"])
        elif operation == "delete":
            self.dynamodb_delete(payload["table"], payload["key"])
        elif operation == "update":
            self.dynamodb_update(
                payload["table"],
                payload["key"],
                payload["update_expression"],
                payload["expression_values"],
            )
        else:
            raise ValueError(f"Unknown DynamoDB push operation: {operation}")

    def _ses_push(self, operation: str, payload: Dict[str, Any], **kwargs: Any) -> None:
        """Route SES push operations."""
        if operation == "send":
            self.ses_send_email(
                to=payload["to"],
                subject=payload["subject"],
                body_text=payload.get("body_text", ""),
                body_html=payload.get("body_html", ""),
                from_addr=payload.get("from_addr"),
            )
        else:
            raise ValueError(f"Unknown SES push operation: {operation}")

    def _cloudwatch_fetch(self, operation: str, **kwargs: Any) -> Any:
        """Route CloudWatch fetch operations."""
        if operation == "query":
            return self.cloudwatch_get_metrics(
                kwargs["namespace"],
                kwargs["metric_name"],
                kwargs["start_time"],
                kwargs["end_time"],
                kwargs.get("period", 300),
                kwargs.get("stat", "Average"),
            )
        else:
            raise ValueError(f"Unknown CloudWatch fetch operation: {operation}")

    def _cloudwatch_push(self, operation: str, payload: Dict[str, Any], **kwargs: Any) -> None:
        """Route CloudWatch push operations."""
        if operation == "metric":
            self.cloudwatch_put_metric(
                payload["namespace"],
                payload["metric_name"],
                payload["value"],
                payload.get("unit", "None"),
                payload.get("dimensions"),
            )
        elif operation == "log":
            self.cloudwatch_log(
                payload["log_group"],
                payload["log_stream"],
                payload["message"],
                payload.get("sequence_token"),
            )
        else:
            raise ValueError(f"Unknown CloudWatch push operation: {operation}")
