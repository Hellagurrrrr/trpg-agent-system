from schemas import NarrativeResponse
from llm_client import chat_json


DM_SYSTEM_PROMPT = """
你是一个TRPG文字跑团系统中的 DM Agent。
你的职责是根据给定的结构化上下文，生成面向玩家的叙事反馈。

你必须遵守以下规则：
1. 只输出 JSON，不要输出任何额外解释。
2. JSON 必须包含以下字段：
   - narrative_text
   - player_options_hint
   - important_notice
3. narrative_text 只描述玩家当前能感知到的内容。
4. 不要编造未提供的关键线索。
5. 不要修改规则结果，不要推翻成功/失败结论。
6. 语气保持悬疑、简洁、可玩。
7. player_options_hint 给出 2~3 个合理的下一步建议。
"""


def generate_narrative_with_llm(user_input: str, parsed_action, rule_result: dict, state: dict) -> NarrativeResponse:
    prompt_payload = {
        "player_action": user_input,
        "parsed_action": parsed_action.model_dump(),
        "rule_result": rule_result,
        "visible_world_state": {
            "current_location": state["world"]["current_location"],
            "nearby_npcs": list(state.get("npcs", {}).keys()),
            "inventory": state["player"].get("inventory", []),
        },
        "tone": "悬疑、轻度紧张"
    }

    raw = chat_json(
        system_message=DM_SYSTEM_PROMPT,
        user_message=str(prompt_payload)
    )
    return NarrativeResponse.model_validate(raw)