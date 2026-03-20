"""可选：在配置好 ZAI_API_KEY 后批量冒烟测试 PM 解析（需网络）。"""
from world_state import init_world_state
from pm_agent import parse_action_with_llm
from schemas import PlayerAction


def main() -> None:
    state = init_world_state(player_name="测试员")
    test_inputs = [
        "我假装成送货员混进庄园",
        "我看看桌上有什么",
        "我说服门卫让我进去",
        "我偷偷翻墙进去",
        "我搜索抽屉里的账本",
    ]

    for i, text in enumerate(test_inputs, start=1):
        print(f"\n玩家(input={i}): {text}")
        pa = PlayerAction.with_now(session_id=state["session_id"], turn_id=i, raw_input=text)
        result = parse_action_with_llm(pa, state)
        print(result.model_dump())


if __name__ == "__main__":
    main()
