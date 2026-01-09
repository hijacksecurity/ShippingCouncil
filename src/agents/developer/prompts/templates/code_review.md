# Code Review Request

## Files to Review

{% for file in files %}
- `{{ file }}`
{% endfor %}

## Review Focus

{% if review_focus %}
{{ review_focus }}
{% else %}
Please review for:
- Code quality and readability
- Potential bugs or edge cases
- Performance considerations
- Security issues
- Adherence to best practices
{% endif %}

## Instructions

1. Read through the specified files
2. Identify any issues or improvements
3. Provide constructive feedback with specific suggestions
4. If changes are needed, make them directly
