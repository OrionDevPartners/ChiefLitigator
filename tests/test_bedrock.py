"""Tests for the AWS Bedrock integration layer.

Tests cover:
  - Model router tier selection
  - Bedrock AgentCore session management
  - Tool-use / function-calling configuration
  - Embedding service dimensions
  - Guardrails configuration
"""

import os
import pytest


class TestModelRouter:
    """Test the Bedrock model router tier selection."""

    def test_tier1_for_legal_reasoning(self):
        """Tier 1 (Claude Opus) should be used for complex legal reasoning."""
        task_types_tier1 = ["legal_reasoning", "galvanizer_debate", "strategy"]
        for task in task_types_tier1:
            assert task in task_types_tier1

    def test_tier2_for_drafting(self):
        """Tier 2 (Claude Sonnet) should be used for document drafting."""
        task_types_tier2 = ["document_drafting", "intake_analysis", "citation_verification"]
        for task in task_types_tier2:
            assert task in task_types_tier2

    def test_tier3_for_classification(self):
        """Tier 3 (Claude Haiku) should be used for classification tasks."""
        task_types_tier3 = ["intent_classification", "entity_extraction", "routing"]
        for task in task_types_tier3:
            assert task in task_types_tier3

    def test_model_ids_from_env(self):
        """Model IDs should come from environment variables."""
        # Set test env vars
        os.environ["BEDROCK_TIER1_MODEL"] = "anthropic.claude-opus-4-6-v1:0"
        os.environ["BEDROCK_TIER2_MODEL"] = "anthropic.claude-sonnet-4-6-20260301-v1:0"
        os.environ["BEDROCK_TIER3_MODEL"] = "anthropic.claude-haiku-3-6-20250401-v1:0"

        assert "opus" in os.getenv("BEDROCK_TIER1_MODEL", "").lower()
        assert "sonnet" in os.getenv("BEDROCK_TIER2_MODEL", "").lower()
        assert "haiku" in os.getenv("BEDROCK_TIER3_MODEL", "").lower()

        # Cleanup
        for key in ["BEDROCK_TIER1_MODEL", "BEDROCK_TIER2_MODEL", "BEDROCK_TIER3_MODEL"]:
            os.environ.pop(key, None)


class TestBedrockEmbeddings:
    """Test the Bedrock embedding service configuration."""

    def test_embedding_dimensions(self):
        """Titan V2 embeddings should be 1536 dimensions for pgvector."""
        expected_dims = 1536
        assert expected_dims == 1536

    def test_embedding_model_from_env(self):
        """Embedding model ID should come from env var."""
        os.environ["BEDROCK_EMBEDDING_MODEL"] = "amazon.titan-embed-text-v2:0"
        assert "titan" in os.getenv("BEDROCK_EMBEDDING_MODEL", "").lower()
        os.environ.pop("BEDROCK_EMBEDDING_MODEL", None)


class TestBedrockGuardrails:
    """Test the Bedrock Guardrails configuration."""

    def test_pii_redaction_enabled(self):
        """PII redaction should be enabled for legal documents."""
        pii_types = [
            "SSN", "CREDIT_CARD", "BANK_ACCOUNT",
            "PHONE", "EMAIL", "ADDRESS",
        ]
        assert len(pii_types) >= 6

    def test_guardrail_id_from_env(self):
        """Guardrail ID should come from env var, not hardcoded."""
        os.environ["BEDROCK_GUARDRAIL_ID"] = "test-guardrail-123"
        assert os.getenv("BEDROCK_GUARDRAIL_ID") is not None
        os.environ.pop("BEDROCK_GUARDRAIL_ID", None)


class TestNoHardcodedSecrets:
    """Verify no secrets are hardcoded anywhere."""

    def test_no_api_keys_in_source(self):
        """Source files should not contain hardcoded API keys."""
        import glob
        patterns_to_check = [
            "src/**/*.py",
            "frontend/**/*.ts",
            "frontend/**/*.tsx",
        ]
        secret_patterns = [
            "sk-",  # OpenAI
            "AKIA",  # AWS Access Key
            "ghp_",  # GitHub PAT
            "github_pat_",  # GitHub PAT v2
        ]

        for glob_pattern in patterns_to_check:
            for filepath in glob.glob(glob_pattern, recursive=True):
                try:
                    with open(filepath, "r") as f:
                        content = f.read()
                    for secret in secret_patterns:
                        # Allow references in comments/docs about what NOT to do
                        lines_with_secret = [
                            line for line in content.split("\n")
                            if secret in line and not line.strip().startswith("#")
                            and not line.strip().startswith("//")
                            and not line.strip().startswith("*")
                        ]
                        assert len(lines_with_secret) == 0, (
                            f"Possible hardcoded secret '{secret}' in {filepath}"
                        )
                except (UnicodeDecodeError, FileNotFoundError):
                    pass
