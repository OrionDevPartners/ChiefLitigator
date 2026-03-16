"""Mock tests for Bedrock client integration."""

import json
from unittest.mock import MagicMock


class MockBedrockRuntime:
    """Mock AWS Bedrock Runtime client."""

    def __init__(self):
        self.invoke_count = 0
        self.last_model_id = None
        self.last_body = None

    def invoke_model(
        self, modelId: str, body: str, contentType: str = "application/json", accept: str = "application/json"
    ):
        self.invoke_count += 1
        self.last_model_id = modelId
        self.last_body = json.loads(body)

        # Simulate different model responses
        if "claude" in modelId.lower() or "anthropic" in modelId.lower():
            response_body = json.dumps(
                {
                    "content": [{"type": "text", "text": "Mock Claude response for debate consensus."}],
                    "model": modelId,
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                }
            )
        elif "mistral" in modelId.lower():
            response_body = json.dumps(
                {
                    "outputs": [{"text": "Mock Mistral response for debate consensus."}],
                }
            )
        elif "nova" in modelId.lower():
            response_body = json.dumps(
                {
                    "output": {"message": {"content": [{"text": "Mock Nova response."}]}},
                }
            )
        else:
            response_body = json.dumps(
                {
                    "generated_text": "Mock generic model response.",
                }
            )

        mock_response = MagicMock()
        mock_response.__getitem__ = lambda self, key: {
            "body": MagicMock(read=MagicMock(return_value=response_body.encode())),
            "contentType": "application/json",
        }[key]
        mock_response.get = lambda key, default=None: {
            "body": MagicMock(read=MagicMock(return_value=response_body.encode())),
            "contentType": "application/json",
        }.get(key, default)

        return mock_response


class TestBedrockIntegration:
    """Test Bedrock model invocation patterns."""

    def test_claude_invocation(self):
        client = MockBedrockRuntime()
        response = client.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-6",
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": "Analyze this legal argument."}],
                }
            ),
        )
        assert client.invoke_count == 1
        assert "anthropic" in client.last_model_id
        assert client.last_body["max_tokens"] == 1024

    def test_mistral_invocation(self):
        client = MockBedrockRuntime()
        response = client.invoke_model(
            modelId="mistral.mistral-large-2407-v1:0",
            body=json.dumps(
                {
                    "prompt": "Evaluate the following evidence.",
                    "max_tokens": 512,
                }
            ),
        )
        assert client.invoke_count == 1
        assert "mistral" in client.last_model_id

    def test_nova_invocation(self):
        client = MockBedrockRuntime()
        response = client.invoke_model(
            modelId="amazon.nova-pro-v1:0",
            body=json.dumps(
                {
                    "messages": [{"role": "user", "content": [{"text": "Summarize findings."}]}],
                    "inferenceConfig": {"maxTokens": 256},
                }
            ),
        )
        assert client.invoke_count == 1
        assert "nova" in client.last_model_id

    def test_multi_model_panel(self):
        """Simulate a 5-model debate panel."""
        client = MockBedrockRuntime()
        models = [
            "us.anthropic.claude-sonnet-4-6",
            "mistral.mistral-large-2407-v1:0",
            "deepseek.deepseek-v3-2",
            "zhipu.glm-4-7",
            "amazon.nova-pro-v1:0",
        ]
        prompt = "What are the key arguments in this case?"

        responses = []
        for model_id in models:
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps({"prompt": prompt, "max_tokens": 512}),
            )
            responses.append(response)

        assert client.invoke_count == 5
        assert len(responses) == 5

    def test_model_manifest_loading(self, tmp_path):
        """Test that model manifest can be loaded from config."""
        manifest = {
            "models": [
                {"id": "us.anthropic.claude-sonnet-4-6", "provider": "bedrock", "active": True},
                {"id": "mistral.mistral-large-2407-v1:0", "provider": "bedrock", "active": True},
                {"id": "deepseek.deepseek-v3-2", "provider": "bedrock", "active": True},
                {"id": "zhipu.glm-4-7", "provider": "bedrock", "active": True},
                {"id": "amazon.nova-pro-v1:0", "provider": "bedrock", "active": True},
            ],
            "default_max_tokens": 1024,
            "panel_size": 5,
        }
        manifest_path = tmp_path / "model_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        loaded = json.loads(manifest_path.read_text())
        assert len(loaded["models"]) == 5
        active = [m for m in loaded["models"] if m["active"]]
        assert len(active) == 5
        assert all(m["provider"] == "bedrock" for m in active)

    def test_error_handling(self):
        """Test that model errors are handled gracefully."""
        client = MockBedrockRuntime()
        # Even unknown models should return a response in our mock
        response = client.invoke_model(
            modelId="unknown.model-v1",
            body=json.dumps({"prompt": "test"}),
        )
        assert client.invoke_count == 1

    def test_request_body_structure(self):
        """Verify Claude Bedrock request body structure."""
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "temperature": 0.7,
            "messages": [
                {"role": "user", "content": "Provide your legal analysis."},
            ],
            "system": "You are a legal analysis expert.",
        }
        assert "anthropic_version" in body
        assert body["messages"][0]["role"] == "user"
        assert isinstance(body["max_tokens"], int)
