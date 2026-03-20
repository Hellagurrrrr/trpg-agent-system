from world_state import init_world_state, apply_result
from pm_agent import parse_action_with_llm
from rules_engine import resolve_check
from dm_agent import generate_narrative_with_llm


def main():
    state = init_world_state()

    print("=== 跑团开始 ===")
    print("当前地点：", state["world"]["current_location"])

    while True:
        user_input = input("\n你要做什么？> ").strip()

        if user_input in ["退出", "exit", "quit"]:
            print("游戏结束。")
            break

        state["turn_id"] += 1

        try:
            parsed_action = parse_action_with_llm(user_input)
        except Exception as e:
            print(f"\n[PM 解析失败] {e}")
            continue

        if parsed_action.requires_check:
            rule_result = resolve_check(parsed_action, state)
        else:
            rule_result = {
                "roll": None,
                "modifier": 0,
                "total": None,
                "difficulty": None,
                "outcome": "none"
            }

        state = apply_result(state, parsed_action, rule_result)

        try:
            narrative = generate_narrative_with_llm(
                user_input=user_input,
                parsed_action=parsed_action,
                rule_result=rule_result,
                state=state
            )
        except Exception as e:
            print(f"\n[DM 生成失败] {e}")
            continue

        print("\n--- 本回合结果 ---")
        print(narrative.narrative_text)

        if narrative.important_notice:
            print("\n提示：", narrative.important_notice)

        if narrative.player_options_hint:
            print("\n你可以尝试：")
            for i, option in enumerate(narrative.player_options_hint, start=1):
                print(f"{i}. {option}")

        print("\n[调试信息]")
        print("解析动作：", parsed_action.model_dump())
        print("判定结果：", rule_result)
        print("当前位置：", state["world"]["current_location"])
        print("守卫警惕：", state["npcs"]["guard"]["alert_level"])


if __name__ == "__main__":
    main()