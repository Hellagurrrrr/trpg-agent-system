"""
DM Agent（表演层）：根据已过检的 rule_result 与可见世界碎片生成叙事，不得改结构化状态。
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from llm_client import DM_MODEL, chat_json_stream
from schemas import NarrativeResponse, ParsedAction


DM_SYSTEM_PROMPT = """
你是一个TRPG文字跑团系统中的 DM Agent。
你的职责是根据给定的结构化上下文，生成面向玩家的叙事反馈。

你必须遵守以下规则：
1. 只输出 JSON，不要输出任何额外解释。
2. JSON 必须包含以下字段：
   - narrative_text
   - player_options_hint（字符串数组）
   - important_notice（可无意义的进度提示则填 null）
3. narrative_text 只描述玩家当前能感知到的内容。
4. 不要编造未在线索列表或上下文中隐含的关键事实。
5. 必须尊重 rule_result 的 outcome（success / failure / critical_*），不得推翻。
6. 语气保持悬疑、简洁、可玩。
7. player_options_hint 给出 2~3 个合理的下一步建议。
"""


def generate_narrative_with_llm(
    user_input: str,
    parsed_action: ParsedAction,
    rule_result: dict,
    state: Mapping[str, Any],
) -> NarrativeResponse:
    """构造 NarrativeContext（README 中的精选上下文），请求 LLM 产出 NarrativeResponse。"""
    guard = state.get("npcs", {}).get("guard", {})
    prompt_payload = {
        "player_action": user_input,
        "parsed_action": parsed_action.model_dump(),
        "rule_result": rule_result,
        "visible_world_state": {
            "current_location": state["world"]["current_location"],
            "time_stage": state["world"].get("time_stage"),
            "chapter": state["world"].get("chapter"),
            "nearby_npcs": list(state.get("npcs", {}).keys()),
            "discovered_clues": state["world"].get("discovered_clues", []),
            "unlocked_locations": state["world"].get("unlocked_locations", []),
            "inventory": state["player"].get("inventory", []),
            "player_hp": state["player"].get("hp"),
            "main_quest": state.get("quests", {}).get("main_quest"),
            "guard_alert_level": guard.get("alert_level"),
            "guard_attitude": guard.get("attitude"),
        },
        "recent_history": state.get("history", {}).get("recent_turns", [])[-5:],
        "tone": "悬疑、轻度紧张",
    }

    raw = chat_json_stream(
        system_message=DM_SYSTEM_PROMPT,
        user_message=json.dumps(prompt_payload, ensure_ascii=False),
        model=DM_MODEL,
        stream_label="DM Agent",
    )
    return NarrativeResponse.model_validate(raw)
