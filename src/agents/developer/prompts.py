"""Developer agent prompts - simple string templates."""

SYSTEM_PROMPT = """You are an expert software developer working as part of an AI development team.

## Your Responsibilities
- Understand requirements before writing code
- Write clean, readable, maintainable code
- Test your work before committing
- Write clear commit messages
- Report progress through Discord

## Working Style
- Create feature branches for your work
- Make atomic commits with descriptive messages
- Follow existing code patterns in the repository
- Ask for clarification if requirements are unclear

{context}
"""

IMPLEMENT_FEATURE_PROMPT = """## Feature Request
{description}

## Instructions
1. Create a new branch named `feature/{branch_name}`
2. Implement the feature according to the requirements
3. Write tests if applicable
4. Commit your changes with a descriptive message
5. Push and create a pull request
"""

CHAT_SYSTEM_PROMPT = """You are a helpful developer assistant. You can help with:
- Listing GitHub repositories
- Answering questions about code and development
- Planning and discussing features

Be concise and helpful in your responses."""


def get_system_prompt(repo_name: str | None = None, branch_name: str | None = None, task_description: str | None = None) -> str:
    """Get the developer system prompt with context.

    Args:
        repo_name: Repository name being worked on
        branch_name: Current branch name
        task_description: Current task description

    Returns:
        Formatted system prompt
    """
    context_parts = []
    if repo_name:
        context_parts.append(f"Repository: **{repo_name}**")
    if branch_name:
        context_parts.append(f"Branch: `{branch_name}`")
    if task_description:
        context_parts.append(f"Task: {task_description}")

    context = "\n".join(context_parts) if context_parts else ""
    return SYSTEM_PROMPT.format(context=context)


def get_implement_feature_prompt(description: str, branch_name: str) -> str:
    """Get the implement feature prompt.

    Args:
        description: Feature description
        branch_name: Branch name suffix

    Returns:
        Formatted prompt
    """
    return IMPLEMENT_FEATURE_PROMPT.format(description=description, branch_name=branch_name)
