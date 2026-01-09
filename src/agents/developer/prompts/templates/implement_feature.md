# Implement Feature

## Feature Request

{{ feature_description }}

## Acceptance Criteria

{% for criterion in acceptance_criteria %}
- {{ criterion }}
{% endfor %}

## Instructions

1. Create a new branch named `feature/{{ branch_suffix }}`
2. Implement the feature according to the requirements
3. Write tests if applicable
4. Commit your changes with a descriptive message
5. Create a pull request to the main branch

{% if additional_context %}
## Additional Context

{{ additional_context }}
{% endif %}
