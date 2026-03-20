"""
PM Agent（控制层）：仅解析与调度，不修改 WorldState，不写最终叙事。
v0.0 输入为 PlayerAction + 世界快照，输出 ParsedAction。
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from llm_client import chat_json_stream
from schemas import ParsedAction, PlayerAction


PM_SYSTEM_PROMPT = """
你是一个TRPG跑团系统中的 PM Agent。
你的职责是把玩家的自然语言输入解析成结构化动作 JSON。

你必须遵守以下规则：
1. 只输出 JSON，不要输出任何额外解释。
2. JSON 必须包含以下字段：
   - action_type
   - intent（可选，简短中文）
   - target
   - method
   - requires_check
   - check_type
   - difficulty（可选，整数 5~20，表示建议 DC；把握不准可省略）
   - preconditions / on_success / on_failure / notes（均可选，字符串数组或字符串）
3. action_type 只能是以下之一：
   move, observe, investigate, talk, persuade, deceive, stealth, take_item, use_item, attack
4. check_type 只能是以下之一：
   strength, agility, intelligence, charisma, none
5. 如果只是观察、简单移动、普通对话、拾取明显可达物品，通常不需要检定。
6. 如果涉及欺骗、潜行、攻击、说服、深入调查，通常需要检定。
7. 若不需要检定，requires_check=false，check_type=none。
8. 不要编造剧情结果，不要输出判定成功或失败，只负责动作解析。
9. 请结合当前世界状态判断行动是否合理（例如地点、在场NPC）；不合理仍可解析，但 preconditions 里写明缺失条件。
"""


def parse_action_with_llm(player_action: PlayerAction, state: Mapping[str, Any]) -> ParsedAction:
    """将玩家输入解析为 ParsedAction；state 仅作上下文，不得以任何形式写回。"""
    world_ctx = {
        "current_location": state["world"]["current_location"],
        "unlocked_locations": state["world"].get("unlocked_locations", []),
        "discovered_clues": state["world"].get("discovered_clues", []),
        "nearby_npcs": list(state.get("npcs", {}).keys()),
        "player_name": state["player"]["name"],
        "main_quest": state.get("quests", {}).get("main_quest"),
    }
    user_payload = {
        "player_action": player_action.model_dump(),
        "world_snapshot": world_ctx,
    }
    raw = chat_json_stream(
        system_message=PM_SYSTEM_PROMPT,
        user_message=json.dumps(user_payload, ensure_ascii=False),
        stream_label="PM Agent",
    )
    return ParsedAction.model_validate(raw)
