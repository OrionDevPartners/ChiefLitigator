"""
Ciphergy Pipeline — Connector Recommendation Engine

Analyzes the user's project description and recommends connectors
with prioritized setup instructions. Uses Bedrock for AI-powered
analysis when available, falls back to rule-based matching.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConnectorRecommendation:
    """A single connector recommendation with context."""

    name: str
    why: str
    priority: int  # 1 (critical) to 5 (nice-to-have)
    setup_steps: List[str] = field(default_factory=list)
    required_credentials: List[str] = field(default_factory=list)
    estimated_setup_time: str = ""
    category: str = ""  # project_mgmt, version_control, cloud, edge, data, etc.


@dataclass
class AdvisorResult:
    """Complete result from the connector advisor."""

    recommendations: List[ConnectorRecommendation]
    analysis_summary: str
    detected_domain: str
    ai_powered: bool = False


# ── Domain connector mapping (rule-based fallback) ──────────────────

DOMAIN_CONNECTORS: Dict[str, List[Dict[str, Any]]] = {
    "legal": [
        {
            "name": "asana",
            "why": "Track cases, deadlines, filings, and inter-team communication",
            "priority": 1,
            "category": "project_mgmt",
            "setup_steps": ["Create Asana PAT", "Set ASANA_PAT env var", "Create project per case/matter"],
            "required_credentials": ["ASANA_PAT"],
            "estimated_setup_time": "10 minutes",
        },
        {
            "name": "github",
            "why": "Version control for legal documents, briefs, and evidence files",
            "priority": 2,
            "category": "version_control",
            "setup_steps": [
                "Create GitHub PAT with repo scope",
                "Set GITHUB_TOKEN env var",
                "Create private repo per matter",
            ],
            "required_credentials": ["GITHUB_TOKEN"],
            "estimated_setup_time": "10 minutes",
        },
        {
            "name": "aws",
            "why": "S3 for document storage, DynamoDB for case indexing, SES for notifications, Bedrock for AI analysis",
            "priority": 1,
            "category": "cloud",
            "setup_steps": [
                "Configure AWS credentials",
                "Create S3 bucket for documents",
                "Create DynamoDB table for case index",
                "Verify Bedrock model access",
            ],
            "required_credentials": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
            "estimated_setup_time": "20 minutes",
        },
    ],
    "startup_dd": [
        {
            "name": "asana",
            "why": "Track due diligence tasks, team assignments, and progress",
            "priority": 1,
            "category": "project_mgmt",
            "setup_steps": [
                "Create Asana PAT",
                "Set ASANA_PAT env var",
                "Create DD project with sections per workstream",
            ],
            "required_credentials": ["ASANA_PAT"],
            "estimated_setup_time": "10 minutes",
        },
        {
            "name": "github",
            "why": "Analyze target company codebase, track DD findings",
            "priority": 1,
            "category": "version_control",
            "setup_steps": ["Create GitHub PAT", "Set GITHUB_TOKEN env var", "Request access to target repos"],
            "required_credentials": ["GITHUB_TOKEN"],
            "estimated_setup_time": "10 minutes",
        },
        {
            "name": "aws",
            "why": "S3 for document room, DynamoDB for findings database, Bedrock for AI analysis",
            "priority": 1,
            "category": "cloud",
            "setup_steps": [
                "Configure AWS credentials",
                "Create S3 bucket for data room",
                "Create DynamoDB table for findings",
            ],
            "required_credentials": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
            "estimated_setup_time": "20 minutes",
        },
    ],
    "medical": [
        {
            "name": "asana",
            "why": "Track patient cases, research tasks, and compliance workflows",
            "priority": 1,
            "category": "project_mgmt",
            "setup_steps": ["Create Asana PAT", "Set ASANA_PAT env var", "Create HIPAA-compliant project structure"],
            "required_credentials": ["ASANA_PAT"],
            "estimated_setup_time": "15 minutes",
        },
        {
            "name": "aws",
            "why": "HIPAA-eligible S3 for records, DynamoDB for patient index, SES for alerts, Bedrock for clinical AI",
            "priority": 1,
            "category": "cloud",
            "setup_steps": [
                "Configure AWS credentials in HIPAA account",
                "Enable S3 encryption",
                "Configure CloudTrail for audit logging",
                "Verify Bedrock access",
            ],
            "required_credentials": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
            "estimated_setup_time": "30 minutes",
        },
    ],
    "software": [
        {
            "name": "github",
            "why": "Source code analysis, PR management, CI/CD workflows, issue tracking",
            "priority": 1,
            "category": "version_control",
            "setup_steps": [
                "Create GitHub PAT with full repo + actions scope",
                "Set GITHUB_TOKEN env var",
                "Configure repo webhooks",
            ],
            "required_credentials": ["GITHUB_TOKEN"],
            "estimated_setup_time": "10 minutes",
        },
        {
            "name": "asana",
            "why": "Sprint planning, task tracking, cross-team coordination",
            "priority": 2,
            "category": "project_mgmt",
            "setup_steps": ["Create Asana PAT", "Set ASANA_PAT env var", "Map to existing sprint board"],
            "required_credentials": ["ASANA_PAT"],
            "estimated_setup_time": "10 minutes",
        },
        {
            "name": "aws",
            "why": "Infrastructure monitoring, S3 artifacts, CloudWatch metrics, Bedrock for code review AI",
            "priority": 1,
            "category": "cloud",
            "setup_steps": [
                "Configure AWS credentials",
                "Set up CloudWatch log groups",
                "Configure Bedrock model access",
            ],
            "required_credentials": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
            "estimated_setup_time": "20 minutes",
        },
        {
            "name": "cloudflare",
            "why": "Edge deployment via Workers, DNS management, KV for feature flags, R2 for assets",
            "priority": 3,
            "category": "edge",
            "setup_steps": [
                "Create Cloudflare API token",
                "Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID",
                "Configure zone",
            ],
            "required_credentials": ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"],
            "estimated_setup_time": "15 minutes",
        },
    ],
}

# Keywords that trigger connector recommendations
KEYWORD_TRIGGERS: Dict[str, List[str]] = {
    "asana": [
        "project management",
        "task tracking",
        "sprint",
        "workflow",
        "team",
        "deadline",
        "milestone",
        "kanban",
        "agile",
    ],
    "github": [
        "code",
        "repository",
        "git",
        "source control",
        "pull request",
        "ci/cd",
        "deployment",
        "version control",
        "open source",
    ],
    "aws": [
        "cloud",
        "storage",
        "database",
        "email",
        "notification",
        "ai",
        "machine learning",
        "bedrock",
        "s3",
        "dynamodb",
        "lambda",
    ],
    "cloudflare": ["cdn", "edge", "dns", "worker", "serverless", "kv", "r2", "pages", "domain", "ssl"],
}


class ConnectorAdvisor:
    """
    Recommends connectors based on project description and domain.

    Uses Bedrock AI for intelligent analysis when available,
    falls back to keyword matching and domain templates.
    """

    MODEL_ID = "us.anthropic.claude-sonnet-4-6-20250514-v1:0"

    def __init__(self, region: str = "us-east-1", model_id: Optional[str] = None) -> None:
        """
        Initialize the connector advisor.

        Args:
            region: AWS region for Bedrock.
            model_id: Override Bedrock model ID.
        """
        self._region = region
        self._model_id = model_id or self.MODEL_ID
        self._bedrock_client: Any = None

    def recommend(
        self,
        project_description: str,
        domain: Optional[str] = None,
        existing_tools: Optional[List[str]] = None,
    ) -> AdvisorResult:
        """
        Analyze a project and return connector recommendations.

        Args:
            project_description: Free-text description of the project.
            domain: Optional domain hint (legal, startup_dd, medical, software).
            existing_tools: Tools the user already has.

        Returns:
            AdvisorResult with prioritized recommendations.
        """
        existing = existing_tools or []

        # Try AI-powered analysis first
        try:
            result = self._ai_recommend(project_description, domain, existing)
            if result:
                return result
        except Exception as exc:
            logger.info("AI recommendation unavailable (%s). Using rule-based.", exc)

        # Fall back to rule-based
        return self._rule_based_recommend(project_description, domain, existing)

    def recommend_for_use_case(self, use_case: str) -> AdvisorResult:
        """
        Get recommendations for a predefined use case.

        Args:
            use_case: One of "legal", "startup_dd", "medical", "software", or "custom".

        Returns:
            AdvisorResult with recommendations for the use case.
        """
        return self._rule_based_recommend(f"Project in the {use_case} domain", use_case, [])

    # ── AI-powered recommendation ───────────────────────────────────

    def _ai_recommend(self, description: str, domain: Optional[str], existing: List[str]) -> Optional[AdvisorResult]:
        """Use Bedrock AI to generate recommendations."""
        if self._bedrock_client is None:
            try:
                import boto3

                session = boto3.Session(region_name=self._region)
                self._bedrock_client = session.client("bedrock-runtime", region_name=self._region)
            except ImportError:
                return None

        prompt = f"""Analyze this project and recommend Ciphergy connectors.

PROJECT: {description}
DOMAIN: {domain or "auto-detect"}
EXISTING TOOLS: {", ".join(existing) or "none"}

Available connectors:
1. asana — Project management, task tracking, inter-agent messaging
2. github — Source code, issues, PRs, Actions, file management
3. aws — S3, DynamoDB, SES, CloudWatch, Bedrock AI models
4. cloudflare — Workers, Pages, DNS, KV storage, R2 storage

For each recommended connector, provide:
- name: connector name
- why: specific reason for this project
- priority: 1 (critical) to 5 (nice-to-have)
- setup_steps: list of setup steps
- required_credentials: list of env vars needed
- estimated_setup_time: time estimate

Also provide:
- analysis_summary: 2-3 sentence analysis of the project
- detected_domain: the domain you detected

Respond with ONLY valid JSON:
{{"recommendations": [...], "analysis_summary": "...", "detected_domain": "..."}}"""

        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}],
            }
        )

        response = self._bedrock_client.invoke_model(
            modelId=self._model_id,
            body=body,
            accept="application/json",
            contentType="application/json",
        )

        response_body = json.loads(response["body"].read())
        content = response_body.get("content", [])
        text = content[0].get("text", "") if content else ""

        # Parse response
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        data = json.loads(text)

        recommendations = [
            ConnectorRecommendation(
                name=r.get("name", ""),
                why=r.get("why", ""),
                priority=r.get("priority", 3),
                setup_steps=r.get("setup_steps", []),
                required_credentials=r.get("required_credentials", []),
                estimated_setup_time=r.get("estimated_setup_time", ""),
                category=r.get("category", ""),
            )
            for r in data.get("recommendations", [])
        ]

        return AdvisorResult(
            recommendations=recommendations,
            analysis_summary=data.get("analysis_summary", ""),
            detected_domain=data.get("detected_domain", domain or "unknown"),
            ai_powered=True,
        )

    # ── Rule-based recommendation ───────────────────────────────────

    def _rule_based_recommend(self, description: str, domain: Optional[str], existing: List[str]) -> AdvisorResult:
        """Generate recommendations using keyword matching and domain templates."""
        detected_domain = domain or self._detect_domain(description)
        recommendations: List[ConnectorRecommendation] = []

        # Get domain-specific recommendations
        domain_recs = DOMAIN_CONNECTORS.get(detected_domain, DOMAIN_CONNECTORS.get("legal", []))

        for rec_data in domain_recs:
            name = rec_data["name"]
            # Adjust priority if tool is already in use
            priority = rec_data["priority"]
            if name in [t.lower() for t in existing]:
                priority = max(1, priority - 1)  # Boost priority for existing tools

            recommendations.append(
                ConnectorRecommendation(
                    name=name,
                    why=rec_data["why"],
                    priority=priority,
                    setup_steps=rec_data["setup_steps"],
                    required_credentials=rec_data["required_credentials"],
                    estimated_setup_time=rec_data["estimated_setup_time"],
                    category=rec_data["category"],
                )
            )

        # Check for keyword-triggered connectors not already recommended
        recommended_names = {r.name for r in recommendations}
        desc_lower = description.lower()

        for connector_name, keywords in KEYWORD_TRIGGERS.items():
            if connector_name in recommended_names:
                continue
            matches = sum(1 for kw in keywords if kw in desc_lower)
            if matches >= 2:
                # Find connector info from any domain template
                for domain_recs_list in DOMAIN_CONNECTORS.values():
                    for rec_data in domain_recs_list:
                        if rec_data["name"] == connector_name:
                            recommendations.append(
                                ConnectorRecommendation(
                                    name=connector_name,
                                    why=f"Detected keywords suggest {connector_name} would be useful",
                                    priority=3,
                                    setup_steps=rec_data["setup_steps"],
                                    required_credentials=rec_data["required_credentials"],
                                    estimated_setup_time=rec_data["estimated_setup_time"],
                                    category=rec_data["category"],
                                )
                            )
                            break
                    else:
                        continue
                    break

        # Sort by priority
        recommendations.sort(key=lambda r: r.priority)

        return AdvisorResult(
            recommendations=recommendations,
            analysis_summary=f"Rule-based analysis for {detected_domain} domain project. "
            f"Found {len(recommendations)} recommended connector(s).",
            detected_domain=detected_domain,
            ai_powered=False,
        )

    def _detect_domain(self, description: str) -> str:
        """Detect domain from project description keywords."""
        desc_lower = description.lower()

        domain_keywords: Dict[str, List[str]] = {
            "legal": [
                "legal",
                "law",
                "court",
                "litigation",
                "plaintiff",
                "defendant",
                "filing",
                "brief",
                "deposition",
                "pro se",
                "case",
                "attorney",
                "counsel",
            ],
            "startup_dd": [
                "startup",
                "due diligence",
                "investment",
                "funding",
                "valuation",
                "equity",
                "cap table",
                "pitch",
                "venture",
            ],
            "medical": [
                "medical",
                "clinical",
                "patient",
                "diagnosis",
                "treatment",
                "health",
                "hipaa",
                "pharma",
                "hospital",
                "healthcare",
            ],
            "software": [
                "software",
                "code",
                "development",
                "api",
                "deploy",
                "infrastructure",
                "devops",
                "frontend",
                "backend",
                "microservice",
            ],
        }

        scores: Dict[str, int] = {}
        for domain_name, keywords in domain_keywords.items():
            scores[domain_name] = sum(1 for kw in keywords if kw in desc_lower)

        if max(scores.values(), default=0) == 0:
            return "legal"  # Default domain

        return max(scores, key=lambda d: scores[d])

    # ── Display helpers ─────────────────────────────────────────────

    def format_report(self, result: AdvisorResult) -> str:
        """
        Format the advisor result as a human-readable report.

        Args:
            result: The AdvisorResult to format.

        Returns:
            Formatted report string.
        """
        lines: List[str] = [
            "=" * 60,
            "  Ciphergy Connector Recommendations",
            "=" * 60,
            "",
            f"  Domain: {result.detected_domain}",
            f"  Analysis: {result.analysis_summary}",
            f"  AI-powered: {'Yes' if result.ai_powered else 'No (rule-based)'}",
            "",
        ]

        for i, rec in enumerate(result.recommendations, 1):
            priority_label = {1: "CRITICAL", 2: "HIGH", 3: "MEDIUM", 4: "LOW", 5: "OPTIONAL"}.get(rec.priority, "?")
            lines.append(f"  [{i}] {rec.name.upper()} (Priority: {priority_label})")
            lines.append(f"      Why: {rec.why}")
            if rec.estimated_setup_time:
                lines.append(f"      Setup time: {rec.estimated_setup_time}")
            if rec.required_credentials:
                lines.append(f"      Credentials: {', '.join(rec.required_credentials)}")
            if rec.setup_steps:
                lines.append("      Steps:")
                for step in rec.setup_steps:
                    lines.append(f"        - {step}")
            lines.append("")

        return "\n".join(lines)
