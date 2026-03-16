"""
Ciphergy Pipeline — Interactive Onboarding Assistant

Uses AWS Bedrock (Claude Sonnet 4.6) to interview the user and auto-generate
a complete Ciphergy configuration: ciphergy.yaml, connector recommendations,
confidence monitor categories, known traps, WDC panel personas, and
monitored file lists.
"""

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Optional rich formatting
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.markdown import Markdown
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class OnboardingState:
    """Tracks the user's answers during onboarding."""

    project_name: str = ""
    project_description: str = ""
    domain: str = ""
    data_sources: List[str] = field(default_factory=list)
    desired_outputs: List[str] = field(default_factory=list)
    team_size: str = ""
    existing_tools: List[str] = field(default_factory=list)
    sensitivity_level: str = "medium"  # low, medium, high, critical
    budget_tier: str = "standard"  # free, standard, professional, enterprise
    custom_notes: str = ""


@dataclass
class GeneratedConfig:
    """The full generated configuration from onboarding."""

    ciphergy_yaml: Dict[str, Any] = field(default_factory=dict)
    recommended_connectors: List[Dict[str, Any]] = field(default_factory=list)
    confidence_categories: List[Dict[str, str]] = field(default_factory=list)
    known_traps: List[Dict[str, str]] = field(default_factory=list)
    wdc_panel_personas: List[Dict[str, Any]] = field(default_factory=list)
    monitored_files: List[str] = field(default_factory=list)


class OnboardingAssistant:
    """
    Interactive AI-powered onboarding assistant for Ciphergy Pipeline.

    Interviews the user about their project, then uses Bedrock to
    generate a complete configuration tailored to their use case.
    """

    MODEL_ID = "us.anthropic.claude-sonnet-4-6-20250514-v1:0"

    def __init__(
        self,
        project_root: Optional[str] = None,
        model_id: Optional[str] = None,
        region: str = "us-east-1",
    ) -> None:
        """
        Initialize the onboarding assistant.

        Args:
            project_root: Root directory of the Ciphergy project.
            model_id: Bedrock model ID to use for generation.
            region: AWS region for Bedrock.
        """
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._config_dir = self._project_root / "config"
        self._model_id = model_id or self.MODEL_ID
        self._region = region
        self._state = OnboardingState()
        self._generated: Optional[GeneratedConfig] = None
        self._console = Console() if HAS_RICH else None
        self._bedrock_client: Any = None

    # ── Public API ──────────────────────────────────────────────────

    def run(self) -> GeneratedConfig:
        """
        Run the full onboarding flow interactively.

        Returns:
            The generated configuration.
        """
        self._print_welcome()
        self._interview()
        self._print_summary()

        self._print_header("Generating Configuration")
        self._print_info("Analyzing your project with AI...")

        self._generated = self._generate_config()

        self._print_header("Configuration Generated")
        self._display_config(self._generated)

        if self._confirm("Save configuration to config/ directory?"):
            self._save_config(self._generated)
            self._print_success("Configuration saved successfully.")
        else:
            self._print_info("Configuration not saved. You can re-run onboarding anytime.")

        return self._generated

    def run_update(self) -> GeneratedConfig:
        """
        Re-run onboarding to update an existing configuration.

        Returns:
            The updated configuration.
        """
        existing = self._load_existing_config()
        if existing:
            self._print_info("Found existing configuration. Updating...")
            self._state = self._state_from_config(existing)

        return self.run()

    def generate_from_description(self, description: str) -> GeneratedConfig:
        """
        Generate configuration from a text description without interactive interview.

        Args:
            description: Free-text project description.

        Returns:
            The generated configuration.
        """
        self._state.project_description = description
        self._state.project_name = description.split()[0] if description else "project"
        self._generated = self._generate_config()
        return self._generated

    # ── Interview ───────────────────────────────────────────────────

    def _interview(self) -> None:
        """Conduct the interactive interview."""
        self._print_header("Project Setup")

        self._state.project_name = self._ask(
            "What is your project name?",
            default="my-project",
        )

        self._state.project_description = self._ask(
            "Describe your project in 1-3 sentences.\n"
            "  (What problem are you solving? What decisions need to be made?)",
        )

        self._state.domain = self._ask(
            "What domain/industry is this for?",
            choices=["legal", "startup_dd", "medical", "software", "research", "finance", "custom"],
            default="legal",
        )

        if self._state.domain == "custom":
            self._state.domain = self._ask("Describe your custom domain:")

        # Data sources
        self._print_info("What data sources will you use? (comma-separated)")
        self._print_info("  Examples: court filings, SEC filings, medical records, GitHub repos,")
        self._print_info("  news feeds, internal documents, APIs, databases")
        sources_raw = self._ask("Data sources:")
        self._state.data_sources = [s.strip() for s in sources_raw.split(",") if s.strip()]

        # Desired outputs
        self._print_info("What outputs do you need? (comma-separated)")
        self._print_info("  Examples: analysis reports, risk assessments, recommendations,")
        self._print_info("  compliance checks, evidence summaries, decision matrices")
        outputs_raw = self._ask("Desired outputs:")
        self._state.desired_outputs = [o.strip() for o in outputs_raw.split(",") if o.strip()]

        # Existing tools
        self._print_info("What tools do you already use? (comma-separated, or 'none')")
        tools_raw = self._ask("Existing tools:", default="none")
        if tools_raw.lower() != "none":
            self._state.existing_tools = [t.strip() for t in tools_raw.split(",") if t.strip()]

        # Sensitivity
        self._state.sensitivity_level = self._ask(
            "Data sensitivity level?",
            choices=["low", "medium", "high", "critical"],
            default="medium",
        )

        # Additional notes
        self._state.custom_notes = self._ask(
            "Any additional notes or requirements? (press Enter to skip)",
            default="",
        )

    # ── Configuration generation ────────────────────────────────────

    def _generate_config(self) -> GeneratedConfig:
        """Generate a full configuration using Bedrock AI."""
        prompt = self._build_generation_prompt()

        try:
            ai_response = self._invoke_bedrock(prompt)
            config = self._parse_ai_response(ai_response)
        except Exception as exc:
            logger.warning("AI generation failed (%s). Using template-based config.", exc)
            config = self._generate_template_config()

        return config

    def _build_generation_prompt(self) -> str:
        """Build the prompt for Bedrock to generate configuration."""
        return f"""You are a Ciphergy Pipeline configuration generator. Based on the user's project description, generate a complete configuration.

PROJECT DETAILS:
- Name: {self._state.project_name}
- Description: {self._state.project_description}
- Domain: {self._state.domain}
- Data Sources: {', '.join(self._state.data_sources) or 'not specified'}
- Desired Outputs: {', '.join(self._state.desired_outputs) or 'not specified'}
- Existing Tools: {', '.join(self._state.existing_tools) or 'none'}
- Sensitivity: {self._state.sensitivity_level}
- Notes: {self._state.custom_notes or 'none'}

Generate a JSON response with these exact keys:

1. "ciphergy_yaml" — Full ciphergy.yaml config as a dict with:
   - project.name, project.description, project.domain
   - connectors (list of connector configs)
   - cascades (trigger definitions)
   - confidence_monitor.categories
   - wdc_panel.models
   - sync settings
   - asana settings

2. "recommended_connectors" — List of dicts with:
   - name, description, priority (1-5), setup_notes

3. "confidence_categories" — List of dicts with:
   - name, description, weight (0.0-1.0)

4. "known_traps" — List of dicts with:
   - trap_id, description, severity (low/medium/high/critical), mitigation

5. "wdc_panel_personas" — List of dicts with:
   - name, role, model_id, system_prompt, weight (0.0-1.0)
   Use these Bedrock models: Claude Sonnet 4.6, Mistral Large 3, DeepSeek V3.2, GLM 4.7, Nova Pro

6. "monitored_files" — List of file glob patterns to track

Respond with ONLY valid JSON, no markdown fences or explanation."""

    def _invoke_bedrock(self, prompt: str) -> str:
        """
        Call Bedrock with the given prompt.

        Args:
            prompt: The prompt to send.

        Returns:
            The model's text response.
        """
        if self._bedrock_client is None:
            try:
                import boto3
                session = boto3.Session(region_name=self._region)
                self._bedrock_client = session.client("bedrock-runtime", region_name=self._region)
            except ImportError:
                raise RuntimeError("boto3 is required for AI generation. Install with: pip install boto3")

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 8192,
            "temperature": 0.3,
            "messages": [{"role": "user", "content": prompt}],
        })

        response = self._bedrock_client.invoke_model(
            modelId=self._model_id,
            body=body,
            accept="application/json",
            contentType="application/json",
        )

        response_body = json.loads(response["body"].read())
        content = response_body.get("content", [])
        return content[0].get("text", "") if content else ""

    def _parse_ai_response(self, response_text: str) -> GeneratedConfig:
        """Parse the AI response into a GeneratedConfig."""
        # Strip markdown code fences if present
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        data = json.loads(text)
        return GeneratedConfig(
            ciphergy_yaml=data.get("ciphergy_yaml", {}),
            recommended_connectors=data.get("recommended_connectors", []),
            confidence_categories=data.get("confidence_categories", []),
            known_traps=data.get("known_traps", []),
            wdc_panel_personas=data.get("wdc_panel_personas", []),
            monitored_files=data.get("monitored_files", []),
        )

    def _generate_template_config(self) -> GeneratedConfig:
        """Generate configuration from templates when AI is unavailable."""
        domain = self._state.domain.lower()

        # Domain-specific trap templates
        trap_templates: Dict[str, List[Dict[str, str]]] = {
            "legal": [
                {"trap_id": "TRAP-001", "description": "Citing overruled precedent", "severity": "critical", "mitigation": "Cross-reference with Shepard's/KeyCite"},
                {"trap_id": "TRAP-002", "description": "Jurisdiction mismatch", "severity": "high", "mitigation": "Verify jurisdiction applies to the case"},
                {"trap_id": "TRAP-003", "description": "Statute of limitations expired", "severity": "critical", "mitigation": "Calendar all deadlines on intake"},
                {"trap_id": "TRAP-004", "description": "Conflicting evidence not flagged", "severity": "high", "mitigation": "Run contradiction detection in WDC panel"},
            ],
            "software": [
                {"trap_id": "TRAP-001", "description": "Outdated dependency versions", "severity": "high", "mitigation": "Run dependency audit before analysis"},
                {"trap_id": "TRAP-002", "description": "Missing security vulnerabilities", "severity": "critical", "mitigation": "Cross-reference CVE databases"},
            ],
            "medical": [
                {"trap_id": "TRAP-001", "description": "Contraindication not flagged", "severity": "critical", "mitigation": "Cross-reference drug interaction databases"},
                {"trap_id": "TRAP-002", "description": "Outdated clinical guidelines", "severity": "high", "mitigation": "Verify against current guidelines"},
            ],
        }

        # WDC panel personas
        personas = [
            {"name": "Analyst", "role": "Primary analysis and evidence synthesis", "model_id": "us.anthropic.claude-sonnet-4-6-20250514-v1:0", "system_prompt": f"You are a senior {domain} analyst. Synthesize evidence methodically.", "weight": 0.3},
            {"name": "Critic", "role": "Devil's advocate — challenges assumptions", "model_id": "mistral.mistral-large-2407-v1:0", "system_prompt": f"You are a critical reviewer in {domain}. Challenge every assumption.", "weight": 0.25},
            {"name": "Researcher", "role": "Deep research and fact verification", "model_id": "us.deepseek.deepseek-v3-2-20250523-v1:0", "system_prompt": f"You are a meticulous researcher in {domain}. Verify every claim.", "weight": 0.2},
            {"name": "Strategist", "role": "Strategic implications and risk assessment", "model_id": "us.zhipu.glm-4-7b-20250515-v1:0", "system_prompt": f"You are a strategic advisor in {domain}. Assess risks and opportunities.", "weight": 0.15},
            {"name": "Integrator", "role": "Synthesis and consensus building", "model_id": "amazon.nova-pro-v1:0", "system_prompt": "You synthesize multiple perspectives into a coherent conclusion.", "weight": 0.1},
        ]

        # Confidence categories
        categories = [
            {"name": "evidence_quality", "description": "Quality and reliability of source evidence", "weight": "0.3"},
            {"name": "model_agreement", "description": "Level of agreement across WDC panel models", "weight": "0.25"},
            {"name": "data_freshness", "description": "How current the underlying data is", "weight": "0.2"},
            {"name": "coverage", "description": "How thoroughly the topic was analyzed", "weight": "0.15"},
            {"name": "contradiction_rate", "description": "Rate of contradictions found in analysis", "weight": "0.1"},
        ]

        # Connectors
        connector_map: Dict[str, List[Dict[str, Any]]] = {
            "legal": [
                {"name": "asana", "description": "Case management and task tracking", "priority": 1, "setup_notes": "Create project per case"},
                {"name": "github", "description": "Document version control and filing storage", "priority": 2, "setup_notes": "One repo per matter"},
                {"name": "aws", "description": "S3 for document storage, DynamoDB for case index", "priority": 1, "setup_notes": "Configure S3 bucket and DynamoDB table"},
            ],
            "software": [
                {"name": "github", "description": "Source code analysis and PR management", "priority": 1, "setup_notes": "Configure repo access"},
                {"name": "asana", "description": "Sprint tracking and issue management", "priority": 2, "setup_notes": "Map to existing project"},
                {"name": "aws", "description": "Infrastructure monitoring and deployment", "priority": 1, "setup_notes": "Configure CloudWatch access"},
                {"name": "cloudflare", "description": "Edge deployment and DNS management", "priority": 3, "setup_notes": "Configure zone access"},
            ],
        }

        # Build ciphergy.yaml
        ciphergy_yaml: Dict[str, Any] = {
            "project": {
                "name": self._state.project_name,
                "description": self._state.project_description,
                "domain": self._state.domain,
                "sensitivity": self._state.sensitivity_level,
                "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            "connectors": {
                c["name"]: {"enabled": True, "priority": c["priority"]}
                for c in connector_map.get(domain, connector_map.get("legal", []))
            },
            "confidence_monitor": {
                "categories": {c["name"]: {"weight": float(c["weight"])} for c in categories}
            },
            "wdc_panel": {
                "models": {
                    p["name"].lower(): {"model_id": p["model_id"], "weight": p["weight"]}
                    for p in personas
                }
            },
            "cascades": {
                "new-evidence": {
                    "description": "New evidence added to the project",
                    "priority": 1,
                    "steps": ["update_registry", "recompute_hashes", "check_alerts", "notify_asana", "sync_check"],
                },
                "phase-change": {
                    "description": "Project phase transition",
                    "priority": 2,
                    "steps": ["update_registry", "recompute_hashes", "full_integrity_check", "escalate_open_items", "notify_asana"],
                },
                "correction": {
                    "description": "Error correction applied",
                    "priority": 1,
                    "steps": ["update_registry", "recompute_hashes", "log_correction", "check_cascading_impacts", "notify_asana"],
                },
            },
            "sync": {"auto_push": True, "interval_minutes": 30},
            "asana": {"enabled": True, "pat_env_var": "ASANA_PAT"},
        }

        return GeneratedConfig(
            ciphergy_yaml=ciphergy_yaml,
            recommended_connectors=connector_map.get(domain, connector_map.get("legal", [])),
            confidence_categories=categories,
            known_traps=trap_templates.get(domain, trap_templates.get("legal", [])),
            wdc_panel_personas=personas,
            monitored_files=["**/*.md", "**/*.pdf", "**/*.docx", "**/*.json", "**/*.yaml", "config/*"],
        )

    # ── Save / Load ─────────────────────────────────────────────────

    def _save_config(self, config: GeneratedConfig) -> None:
        """Save the generated configuration to the config/ directory."""
        self._config_dir.mkdir(parents=True, exist_ok=True)

        # Save ciphergy.yaml
        yaml_path = self._config_dir / "ciphergy.yaml"
        if HAS_YAML:
            with open(yaml_path, "w") as f:
                yaml.dump(config.ciphergy_yaml, f, default_flow_style=False, sort_keys=False)
        else:
            # Fallback: save as JSON
            with open(yaml_path, "w") as f:
                json.dump(config.ciphergy_yaml, f, indent=2)
        logger.info("Saved: %s", yaml_path)

        # Save connectors recommendation
        connectors_path = self._config_dir / "recommended_connectors.json"
        with open(connectors_path, "w") as f:
            json.dump(config.recommended_connectors, f, indent=2)
        logger.info("Saved: %s", connectors_path)

        # Save confidence categories
        confidence_path = self._config_dir / "confidence_categories.json"
        with open(confidence_path, "w") as f:
            json.dump(config.confidence_categories, f, indent=2)
        logger.info("Saved: %s", confidence_path)

        # Save known traps
        traps_path = self._config_dir / "known_traps.json"
        with open(traps_path, "w") as f:
            json.dump(config.known_traps, f, indent=2)
        logger.info("Saved: %s", traps_path)

        # Save WDC panel personas
        personas_path = self._config_dir / "wdc_panel_personas.json"
        with open(personas_path, "w") as f:
            json.dump(config.wdc_panel_personas, f, indent=2)
        logger.info("Saved: %s", personas_path)

        # Save monitored files list
        monitored_path = self._config_dir / "monitored_files.json"
        with open(monitored_path, "w") as f:
            json.dump(config.monitored_files, f, indent=2)
        logger.info("Saved: %s", monitored_path)

    def _load_existing_config(self) -> Optional[Dict[str, Any]]:
        """Load existing ciphergy.yaml if present."""
        yaml_path = self._config_dir / "ciphergy.yaml"
        if not yaml_path.exists():
            return None

        try:
            if HAS_YAML:
                with open(yaml_path) as f:
                    return yaml.safe_load(f)
            else:
                with open(yaml_path) as f:
                    return json.load(f)
        except Exception as exc:
            logger.warning("Failed to load existing config: %s", exc)
            return None

    def _state_from_config(self, config: Dict[str, Any]) -> OnboardingState:
        """Reconstruct onboarding state from an existing config."""
        project = config.get("project", {})
        return OnboardingState(
            project_name=project.get("name", ""),
            project_description=project.get("description", ""),
            domain=project.get("domain", ""),
            sensitivity_level=project.get("sensitivity", "medium"),
        )

    # ── Display helpers ─────────────────────────────────────────────

    def _print_welcome(self) -> None:
        """Print the welcome message."""
        title = "Ciphergy Pipeline — Onboarding Assistant"
        subtitle = "Let's configure your project for multi-model AI analysis."
        if self._console:
            self._console.print(Panel(f"[bold]{title}[/bold]\n{subtitle}", style="blue"))
        else:
            print(f"\n{'='*60}")
            print(f"  {title}")
            print(f"  {subtitle}")
            print(f"{'='*60}\n")

    def _print_header(self, text: str) -> None:
        """Print a section header."""
        if self._console:
            self._console.print(f"\n[bold cyan]--- {text} ---[/bold cyan]\n")
        else:
            print(f"\n--- {text} ---\n")

    def _print_info(self, text: str) -> None:
        """Print an informational message."""
        if self._console:
            self._console.print(f"  [dim]{text}[/dim]")
        else:
            print(f"  {text}")

    def _print_success(self, text: str) -> None:
        """Print a success message."""
        if self._console:
            self._console.print(f"  [bold green]{text}[/bold green]")
        else:
            print(f"  [OK] {text}")

    def _print_summary(self) -> None:
        """Print a summary of the user's answers."""
        self._print_header("Project Summary")
        items = [
            ("Project", self._state.project_name),
            ("Domain", self._state.domain),
            ("Data Sources", ", ".join(self._state.data_sources) or "none specified"),
            ("Outputs", ", ".join(self._state.desired_outputs) or "none specified"),
            ("Sensitivity", self._state.sensitivity_level),
        ]

        if self._console:
            table = Table(show_header=False)
            table.add_column("Field", style="bold")
            table.add_column("Value")
            for label, value in items:
                table.add_row(label, value)
            self._console.print(table)
        else:
            for label, value in items:
                print(f"  {label:20s} {value}")

    def _display_config(self, config: GeneratedConfig) -> None:
        """Display the generated configuration."""
        self._print_info(f"Connectors: {len(config.recommended_connectors)}")
        for c in config.recommended_connectors:
            self._print_info(f"  - {c.get('name', '?')}: {c.get('description', '')}")

        self._print_info(f"Confidence categories: {len(config.confidence_categories)}")
        self._print_info(f"Known traps: {len(config.known_traps)}")
        self._print_info(f"WDC panel personas: {len(config.wdc_panel_personas)}")
        self._print_info(f"Monitored file patterns: {len(config.monitored_files)}")

    def _ask(self, prompt: str, default: str = "", choices: Optional[List[str]] = None) -> str:
        """Ask the user a question."""
        if self._console and HAS_RICH:
            return Prompt.ask(f"  {prompt}", default=default or None, choices=choices) or default
        else:
            suffix = ""
            if choices:
                suffix = f" [{'/'.join(choices)}]"
            if default:
                suffix += f" (default: {default})"
            answer = input(f"  {prompt}{suffix}: ").strip()
            if not answer:
                return default
            if choices and answer not in choices:
                print(f"  Invalid choice. Using default: {default}")
                return default
            return answer

    def _confirm(self, prompt: str) -> bool:
        """Ask the user a yes/no question."""
        if self._console and HAS_RICH:
            return Confirm.ask(f"  {prompt}")
        else:
            answer = input(f"  {prompt} [y/n]: ").strip().lower()
            return answer in ("y", "yes")


# ── CLI entry point ─────────────────────────────────────────────────

def main() -> None:
    """Run the onboarding assistant from the command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Ciphergy Pipeline — Onboarding Assistant")
    parser.add_argument("--project-root", default=None, help="Project root directory")
    parser.add_argument("--model-id", default=None, help="Bedrock model ID")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--update", action="store_true", help="Update existing configuration")
    parser.add_argument("--description", default=None, help="Non-interactive: generate from description")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    assistant = OnboardingAssistant(
        project_root=args.project_root,
        model_id=args.model_id,
        region=args.region,
    )

    if args.description:
        config = assistant.generate_from_description(args.description)
        print(json.dumps({
            "connectors": config.recommended_connectors,
            "traps": config.known_traps,
            "personas": config.wdc_panel_personas,
        }, indent=2))
    elif args.update:
        assistant.run_update()
    else:
        assistant.run()


if __name__ == "__main__":
    main()
