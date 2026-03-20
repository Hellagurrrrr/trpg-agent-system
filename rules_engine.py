"""
规则引擎（可信判定层）：掷骰、DC、成败与结构化 mechanical_effects。
v0.0 仅 d20 + 属性加值 + 临界；不负责叙事、不直接持有完整 WorldState 的写权限。
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping

from schemas import ParsedAction, RuleResult


def roll_d20() -> int:
    return random.randint(1, 20)


def get_modifier(state: Mapping[str, Any], check_type: str) -> int:
    if check_type == "none":
        return 0
    attrs = state["player"].get("attributes") or {}
    return int(attrs.get(check_type, 0))


def infer_difficulty(parsed_action: ParsedAction) -> int:
    """
    当 PM 未给出 difficulty 时的保守默认 DC。
    若有 LLM 输出的 difficulty，优先采用（见 resolve_check）。
    """
    if parsed_action.difficulty is not None:
        return int(parsed_action.difficulty)

    action_type = parsed_action.action_type
    target = (parsed_action.target or "").lower()

    if action_type == "deceive" and ("守卫" in target or "门" in target or "卫" in target):
        return 12
    if action_type == "deceive":
        return 13
    if action_type == "stealth":
        return 10
    if action_type == "investigate":
        return 10
    if action_type == "persuade":
        return 11
    if action_type == "attack":
        return 10

    return 8


def _at_manor_gate(state: Mapping[str, Any]) -> bool:
    return state["world"].get("current_location") == "庄园门口"


def _manor_entry_success_effects() -> List[Dict[str, Any]]:
    """成功混入/说服/潜行进入庄园后的最小可玩扩展：外院 + 若干相邻可移动地点。"""
    return [
        {"type": "location_change", "value": "庄园外院"},
        {"type": "location_unlock", "value": "庄园外院"},
        {"type": "location_unlock", "value": "厨房"},
        {"type": "location_unlock", "value": "主屋侧门"},
        {"type": "npc_alert_change", "target": "guard", "delta": -1},
        {"type": "history_append", "value": "玩家进入庄园外院，门卫未再阻拦。"},
    ]


def build_mechanical_effects(
    state: Mapping[str, Any],
    parsed: ParsedAction,
    outcome: str,
) -> List[Dict[str, Any]]:
    """
    由「动作类型 + 成败 + 当前地点」推导程序化可执行效果。
    复杂剧情应用 StateUpdate 队列也可，此处 mechanical_effects 与之等价。
    """
    effects: List[Dict[str, Any]] = []
    ok = outcome in ("success", "critical_success")
    fail = outcome in ("failure", "critical_failure")
    at = parsed.action_type
    gate = _at_manor_gate(state)

    # 庄园门口：伪装、说服、潜行 —— 成功统一进外院；失败共用水准加怀疑
    if gate and at in ("deceive", "persuade", "stealth"):
        if ok:
            effects.extend(_manor_entry_success_effects())
        elif fail:
            effects.append({"type": "npc_alert_change", "target": "guard", "delta": 1})
            effects.append({"type": "history_append", "value": "门卫对玩家起疑，气氛紧张。"})
        return effects

    if at == "investigate":
        if ok:
            label = parsed.target or parsed.method or "现场"
            effects.append({"type": "clue_add", "value": f"关于「{label}」的调查线索"})
            effects.append({"type": "history_append", "value": f"调查「{label}」有所发现。"})
        else:
            effects.append({"type": "history_append", "value": "调查没有明显结果。"})

    elif at == "attack":
        if ok:
            effects.append({"type": "npc_alert_change", "target": "guard", "delta": 2})
            effects.append({"type": "history_append", "value": "攻击命中或压制了对方，局势急剧升级。"})
        else:
            effects.append({"type": "history_append", "value": "攻击落空或未能奏效。"})

    elif at == "persuade":
        if ok:
            effects.append({"type": "history_append", "value": "说服取得一定进展。"})
        else:
            effects.append({"type": "history_append", "value": "说服未能打动对方。"})

    elif at == "stealth":
        if ok:
            effects.append({"type": "history_append", "value": "潜行未暴露行踪。"})
        else:
            effects.append({"type": "npc_alert_change", "target": "guard", "delta": 1})
            effects.append({"type": "history_append", "value": "潜行时引起了注意。"})

    elif at == "deceive":
        if ok:
            effects.append({"type": "history_append", "value": "欺骗或伪装话术在此场合奏效。"})
        else:
            effects.append({"type": "npc_alert_change", "target": "guard", "delta": 1})
            effects.append({"type": "history_append", "value": "对方对玩家的说辞心存怀疑。"})

    return effects


def resolve_check(turn_id: int, parsed_action: ParsedAction, state: MutableMapping[str, Any]) -> Dict[str, Any]:
    """
    执行一次检定并返回 RuleResult 字典（供 DM 与世界状态更新）。
    critical：天然 1 / 20；outcome 仍区分 critical_success / critical_failure。
    """
    difficulty = infer_difficulty(parsed_action)
    roll = roll_d20()
    modifier = get_modifier(state, parsed_action.check_type)
    total = roll + modifier

    if roll == 20:
        outcome: str = "critical_success"
    elif roll == 1:
        outcome = "critical_failure"
    elif total >= difficulty:
        outcome = "success"
    else:
        outcome = "failure"

    critical = roll in (1, 20)
    mech = build_mechanical_effects(state, parsed_action, outcome)

    rr = RuleResult(
        turn_id=turn_id,
        roll=roll,
        modifier=modifier,
        total=total,
        difficulty=difficulty,
        outcome=outcome,  # type: ignore[arg-type]
        critical=critical,
        mechanical_effects=mech,
    )
    return rr.model_dump()
