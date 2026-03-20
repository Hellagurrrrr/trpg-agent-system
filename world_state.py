def init_world_state():
    return {
        "turn_id": 0,
        "player": {
            "name": "玩家",
            "hp": 10,
            "attributes": {
                "strength": 1,
                "agility": 2,
                "intelligence": 2,
                "charisma": 2
            },
            "inventory": []
        },
        "world": {
            "current_location": "庄园门口",
            "unlocked_locations": ["庄园门口"]
        },
        "npcs": {
            "guard": {
                "alert_level": 2
            }
        },
        "history": []
    }


def apply_result(state, parsed_action, rule_result):
    action_type = parsed_action.action_type

    if not parsed_action.requires_check:
        if action_type == "observe":
            state["history"].append("玩家观察了周围环境")
        return state

    if action_type == "deceive":
        if rule_result["outcome"] in ["success", "critical_success"]:
            state["world"]["current_location"] = "庄园外院"
            if "庄园外院" not in state["world"]["unlocked_locations"]:
                state["world"]["unlocked_locations"].append("庄园外院")
            state["npcs"]["guard"]["alert_level"] -= 1
            state["history"].append("成功混入庄园")
        else:
            state["npcs"]["guard"]["alert_level"] += 1
            state["history"].append("被守卫怀疑")

    elif action_type == "persuade":
        if rule_result["outcome"] in ["success", "critical_success"]:
            state["history"].append("成功说服目标")
        else:
            state["history"].append("说服失败")

    elif action_type == "investigate":
        if rule_result["outcome"] in ["success", "critical_success"]:
            state["history"].append("调查有所发现")
        else:
            state["history"].append("调查没有明显结果")

    elif action_type == "stealth":
        if rule_result["outcome"] in ["success", "critical_success"]:
            state["history"].append("成功潜行")
        else:
            state["history"].append("潜行时发出了动静")

    elif action_type == "attack":
        if rule_result["outcome"] in ["success", "critical_success"]:
            state["history"].append("攻击命中")
        else:
            state["history"].append("攻击落空")

    return state