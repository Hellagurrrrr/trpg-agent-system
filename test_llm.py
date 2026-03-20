from pm_agent import parse_action_with_llm


def main():
    test_inputs = [
        "我假装成送货员混进庄园",
        "我看看桌上有什么",
        "我说服门卫让我进去",
        "我偷偷翻墙进去",
        "我搜索抽屉里的账本",
    ]

    for text in test_inputs:
        print(f"\n玩家输入: {text}")
        result = parse_action_with_llm(text)
        print(result.model_dump())


if __name__ == "__main__":
    main()