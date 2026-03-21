"""
v0.0 入口：角色创建 → 固定模组「庄园调查案」→ 解析→检定→状态→叙事的闭环 CLI。
"""
from __future__ import annotations

import time

from dm_agent import generate_narrative_with_llm
from llm_client import DM_MODEL, PM_MODEL
from pm_agent import parse_action_with_llm
from rules_engine import resolve_check
from schemas import PlayerAction, RuleResult
from world_state import apply_result, init_world_state


MODULE_INTRO = """
╔══════════════════════════════════════════════════════════╗
║  模组：庄园调查案（v0.0 预设）                            ║
║  傍晚，你站在庄园门口。门卫打量着每一个靠近的人。          ║
║  主线：进入庄园并寻找账本。                                ║
╚══════════════════════════════════════════════════════════╝
"""


def _empty_rule_result(turn_id: int) -> dict:
    """本回合无需检定时，仍提供与 RuleResult 同形的占位，便于 DM 与调试。"""
    return RuleResult(
        turn_id=turn_id,
        roll=None,
        modifier=0,
        total=None,
        difficulty=0,
        outcome="none",
        critical=False,
        mechanical_effects=[],
    ).model_dump()


def main() -> None:
    print(MODULE_INTRO.strip())
    name = input("为你的调查员起名（回车默认「林舟」）: ").strip() or "林舟"

    state = init_world_state(player_name=name)

    print("\n── 角色卡（v0.0 属性固定）──")
    print(f"姓名：{state['player']['name']}  HP：{state['player']['hp']}")
    print("属性：", state["player"]["attributes"])
    input("\n按回车开始游戏…")

    print("\n=== 跑团开始 ===")
    print(f"LLM 模型：PM={PM_MODEL} · DM={DM_MODEL}")
    print("当前地点：", state["world"]["current_location"])
    print("主线：", state["quests"]["main_quest"]["description"])

    while True:
        user_input = input("\n你要做什么？> ").strip()

        if user_input in ["退出", "exit", "quit"]:
            print("游戏结束。")
            break

        state["turn_id"] += 1

        player_action = PlayerAction.with_now(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            raw_input=user_input,
        )

        try:
            print("\n… 正在解析行动（PM）…", flush=True)
            t_pm0 = time.perf_counter()
            parsed_action = parse_action_with_llm(player_action, state)
            pm_elapsed_s = time.perf_counter() - t_pm0
        except Exception as e:
            print(f"\n[PM 解析失败] {e}")
            continue

        if parsed_action.requires_check:
            rule_result = resolve_check(state["turn_id"], parsed_action, state)
        else:
            rule_result = _empty_rule_result(state["turn_id"])

        state = apply_result(state, parsed_action, rule_result)

        try:
            print("… 正在生成叙事（DM）…", flush=True)
            t_dm0 = time.perf_counter()
            narrative = generate_narrative_with_llm(
                user_input=user_input,
                parsed_action=parsed_action,
                rule_result=rule_result,
                state=state,
            )
            dm_elapsed_s = time.perf_counter() - t_dm0
        except Exception as e:
            print(f"\n[DM 生成失败] {e}")
            continue

        print("\n--- 本回合结果 ---")
        print(narrative.narrative_text)

        if narrative.important_notice:
            print("\n提示：", narrative.important_notice)

        print("\n[调试信息]")
        print(
            f"本回合耗时：PM {pm_elapsed_s:.2f}s · DM {dm_elapsed_s:.2f}s · 合计 {pm_elapsed_s + dm_elapsed_s:.2f}s"
        )
        print("解析动作：", parsed_action.model_dump())
        print("判定结果：", rule_result)
        print("当前位置：", state["world"]["current_location"])
        print("已解锁地点：", state["world"]["unlocked_locations"])
        print("线索：", state["world"]["discovered_clues"])
        print("守卫警惕：", state["npcs"]["guard"]["alert_level"])
        recent = state.get("history", {}).get("recent_turns", [])
        if recent:
            print("最近记录：", recent[-1])


if __name__ == "__main__":
    main()
