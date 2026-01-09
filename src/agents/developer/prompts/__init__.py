"""Developer agent prompts."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

PROMPTS_DIR = Path(__file__).parent


class DeveloperPrompts:
    """Prompt loader for developer agent."""

    def __init__(self):
        self.prompts_dir = PROMPTS_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            autoescape=select_autoescape(default=False),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def get_system_prompt(self, **context: Any) -> str:
        """Get the developer system prompt with optional context.

        Args:
            **context: Variables for template rendering

        Returns:
            Rendered system prompt
        """
        template = self.env.get_template("system.md")
        return template.render(**context)

    def get_template(self, name: str, **context: Any) -> str:
        """Get a developer prompt template.

        Args:
            name: Template name (without .md extension)
            **context: Variables for template rendering

        Returns:
            Rendered template content
        """
        template = self.env.get_template(f"templates/{name}.md")
        return template.render(**context)


# Singleton instance
_prompts: DeveloperPrompts | None = None


def get_prompts() -> DeveloperPrompts:
    """Get the developer prompts instance."""
    global _prompts
    if _prompts is None:
        _prompts = DeveloperPrompts()
    return _prompts
