from typing import Any


def evaluate_branch(
    branching_config: dict[str, Any],
    ai_output: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate branching config against AI output to select the correct action.

    branching_config shape:
    {
        condition_field: str,
        branches: [{when: value, action: {...}}, ...],
        default_action: {...} | None
    }

    Returns the matched action config dict, or raises ValueError if no match
    and no default.
    """
    condition_field = branching_config.get("condition_field")
    if not condition_field:
        raise ValueError("branching config missing 'condition_field'")

    actual_value = ai_output.get(condition_field)
    branches = branching_config.get("branches", [])

    for branch in branches:
        when_value = branch.get("when")
        # Coerce comparison: both to string for flexibility
        if str(actual_value).lower() == str(when_value).lower():
            action = branch.get("action")
            if not action:
                raise ValueError(f"Branch matched '{when_value}' but has no action defined")
            return action

    # No branch matched — use default
    default_action = branching_config.get("default_action")
    if default_action:
        return default_action

    raise ValueError(
        f"No branch matched condition_field='{condition_field}' "
        f"value='{actual_value}' and no default_action defined"
    )