import random


def roll_d20():
    return random.randint(1, 20)


def get_modifier(state, check_type):
    return state["player"]["attributes"].get(check_type, 0)


def infer_difficulty(parsed_action) -> int:
    action_type = parsed_action.action_type
    target = (parsed_action.target or "").lower()

    if action_type == "deceive" and "guard" in target:
        return 12
    if action_type == "stealth":
        return 10
    if action_type == "investigate":
        return 10
    if action_type == "persuade":
        return 11
    if action_type == "attack":
        return 10

    return 8


def resolve_check(parsed_action, state):
    difficulty = infer_difficulty(parsed_action)

    roll = roll_d20()
    modifier = get_modifier(state, parsed_action.check_type)
    total = roll + modifier

    if roll == 20:
        outcome = "critical_success"
    elif roll == 1:
        outcome = "critical_failure"
    elif total >= difficulty:
        outcome = "success"
    else:
        outcome = "failure"

    return {
        "roll": roll,
        "modifier": modifier,
        "total": total,
        "difficulty": difficulty,
        "outcome": outcome
    }