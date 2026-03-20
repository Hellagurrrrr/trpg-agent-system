# TT的奇妙文字冒险-Agent跑团系统

## 环境与模型（可选）

- 在 `.env` 中配置 `ZAI_API_KEY`（必填）。
- **阶段 A 分模型**（降低延迟）：`ZAI_PM_MODEL` 默认 `glm-4-flash`（动作解析）；`ZAI_DM_MODEL` 或 `ZAI_MODEL` 默认 `glm-4.7`（叙事）。名称需与[智谱开放平台](https://open.bigmodel.cn)一致。
- CLI 每回合会打印 PM/DM 阶段提示与「本回合耗时」，便于对比调参。

## 项目简介：
《TT的奇妙文字冒险》是一个面向文字跑团场景的多 agent 剧情主持系统。系统将传统主持人的职责拆分为叙事 DM、流程 PM、规则裁定器和世界状态管理器，通过 LLM + 规则引擎 + 结构化记忆，实现长剧情、一致设定和可追踪状态的 TRPG 体验。

# 系统功能

### 1. 开团前

- 介绍世界观和模组背景
- 帮玩家创建角色
- 解释规则
- 生成角色关系、初始物品、初始任务、世界地图

### 2. 跑团中

- DM 负责描述场景
- 玩家用自然语言行动
- 系统自动判断：
    - 是否需要检定
    - 用什么属性检定
    - 难度是多少
    - 成功/失败的后果
- NPC 自动对话、反应
- 自动维护：
    - HP / SAN / MP / 金钱 / 背包
    - 任务进度
    - 已发现线索
    - 地图状态
    - 时间推进

### 3. 跑团后

- 自动生成 session summary
- 生成“本次关键剧情回顾”
- 给 玩家展示内容解锁情况

# 游戏流程

## 初始化阶段（开团前）

- **世界初始化**：系统提示玩家选择世界类型（例：异世界勇者、地下城探险、修真者大陆），玩家选择后，系统根据选项生成世界。
- **剧情初始化**：系统随机生成主线任务章节以及主要出场角色（可选：角色间的关系），并分配这些角色的位置。之后，系统将玩家介绍世界观和模组背景，并解释规则
- **玩家角色初始化**：系统提示玩家录入角色信息，包括名字、性格、背景故事、属性点分配（属性点数总和需不能超过一个上限值）。确认合规后，系统将玩家角色信息录入。

## 游戏阶段（开团中）

- **进入主线章节**：（若游戏章节为第一章/初始章节，系统强制将玩家传送至任务地点）系统公布主线任务目标。
- **描述环境**：每当玩家到达一个地点/采取行动后，系统需对当前的情况进行描述（生成叙事）。
- **指令响应**：每当玩家出入指令/提出问题时，系统需提供回应。
- **判断任务**：系统需对任务的完成情况进行判断，如果任务完成，需任务结算+奖励结算+自动存档。若完成任务为主线章节任务，则继续推进主线章节。

## 结算阶段（开团后）

若主线最终任务完成，系统将进入结算阶段。系统将自动生成跑团总结以及展示主要角色、支线任务、地图的解锁情况。

# 系统结构设计

## 1. DM Agent

这是“表演层”。

职责：

- 描述场景
- 扮演 NPC
- 给出剧情反馈
- 渲染氛围
- 在规则允许范围内制造戏剧性

输入：

- 当前世界状态
- 玩家行动
- PM 给的流程约束
- Rules Engine 给的判定结果

输出：

- 对玩家可见的叙事文本
- 需要判定的动作请求

它不应该直接改数据库，也不应该直接拍脑袋判定成功失败。它负责“讲”，不负责“算”。

## 2. PM Agent

这是“控制层”。

职责：

- 管 session 流程
- 检查玩家输入是否缺信息
- 判断当前处于哪个剧情阶段
- 控制节奏，避免剧情失控
- 协调 DM / Rules / Memory
- 自动生成任务列表~~、线索清单、下一步建议~~

它像一个 orchestration agent。

例如玩家说：

> 我要偷偷翻窗进屋找证据
> 

PM agent 会先做拆解：

- 这是潜行行动
- 可能需要 Stealth 检定
- 如果进屋成功，后续可能触发 Investigation
- 当前剧情阶段允许进入该场景
- 屋内有哪些可交互对象要从世界状态中读取

然后再调用其他模块。

## 3. Rules Engine

这是“可信判定层”。

职责：

- 检定计算
- 掷骰
- 难度判定
- 状态变化
- 战斗/调查/社交等结果更新

**真正的规则执行需写成程序。**比如：

- d20 / d100 掷骰
- 属性加值
- 对抗检定
- SAN 减少
- 伤害结算
- 背包增减

## 4. Memory / World State

这是“长期一致性层”。至少要分三种记忆：

### 短期记忆

当前对话上下文

比如最近几轮发生了什么

### 结构化状态

适合程序维护：

- 玩家角色属性
- HP / SAN / 物品 / 金钱
- 当前地点
- 当前时间
- 已完成任务
- 已发现线索
- NPC 好感度 / 阵营

### 长期叙事记忆

适合总结存档：

- 发生过的关键剧情
- 玩家做过的重要选择
- 世界观设定
- NPC 背景
- 伏笔

真正可用的系统不能只靠聊天记录，不然几轮后就会失忆、吃设定。

## 5. Module / Campaign Manager

这是“剧本层”。职责：

- 读取模组
- 维护章节节点
- 管理可触发事件
- 控制主线 / 支线
- 防止剧情彻底崩坏

因为“完整剧情”不能只靠 LLM 临场发挥。最好有一个**半结构化剧情图，例如**：

- Chapter 1：进入村庄
- Chapter 2：发现尸体
- Chapter 3：调查三名嫌疑人
- Chapter 4：地窖真相
- Chapter 5：结局分歧

每章包含：

- 必达节点
- 可选节点
- 触发条件
- 失败条件
- 关键线索

这样 DM 才不会无限发散。

# 系统工作流

## Case1：玩家输入动作指令

### Step 1：玩家输入

“我想假装成送货员混进庄园。”

### Step 2：PM Agent 解析意图

输出结构化任务：

- action_type: deception_infiltration
- target: manor
- needs_check: true
- check_type: disguise / persuasion
- possible_consequences: allowed / suspicious / exposed

### Step 3：Rules Engine 执行

- 掷骰
- 算角色属性
- 输出判定结果

例如：

- roll = 42
- skill = Persuasion 55
- result = success

### Step 4：World State 更新

- 玩家进入庄园外院
- 门卫对玩家警惕度 -1
- 新场景解锁：厨房、走廊、储藏室

### Step 5：DM Agent 生成叙事

“门卫皱着眉打量了你两秒，最终还是侧身让开。你拎着木箱跨过铁门，潮湿的石板路一直通向主屋侧门。空气里有一股淡淡的消毒水味，而厨房方向，似乎有人正在争吵。”

### Step 6：PM Agent 生成辅助信息

- 当前目标：进入庄园并寻找账本

# V0.0

v0.0作为启动版本，只包含**最基础的**可运行功能，既：

*单人玩家，在固定模组中，通过自然语言进行行动，系统完成一次完整的“解析 → 判定 → 状态更新 → 叙事反馈”的循环。*

## 玩家体验流程：

玩家进入游戏后可以：

1. 创建角色（简化版）
2. 进入一个固定剧情场景
3. 输入一句自然语言行动
    
    👉 例如：「我假装送货员混进去」
    

系统必须做到：

- 理解意图（PM）
- 判断是否需要检定（PM + Rules）
- 掷骰并计算结果（Rules）
- 更新世界（World State）
- 生成叙事反馈（DM）

👉 然后回到下一轮

## 当前版本功能：

只保留“闭环必须的东西”：

---

### 1️⃣ 世界 & 剧情

- ✅ 只允许 **1个预设模组**
- ✅ 固定剧情结构：庄园调查案
- ❌ 不做自由世界生成
- ❌ 不做多结局复杂分支（可以有简单分支）

---

### 2️⃣ 角色系统

- ✅ 4 个属性：力量、敏捷、智力、魅力
- ✅ 1 个基础状态：生命值
- ✅ 初始数值固定
- ❌ 不做复杂技能树
- ❌ 不做完整装备系统（仅支持简单物品持有）

---

### 3️⃣ 行动解析（PM核心）

- ✅ 识别 action_type（潜行/ 说服/ 调查/攻击）
- ✅ 判断是否需要检定
- ❌ 不追求100%准确（允许模糊）

---

### 4️⃣ 规则系统（Rules Engine）

- ✅ d20
- ✅ 属性加值
- ✅ 成功 / 失败 / 临界
- ❌ 不做复杂战斗系统

---

### 5. 世界状态（World State）

- ✅ 记录玩家当前位置
- ✅ 记录玩家生命值
- ✅ 记录玩家持有物品
- ✅ 记录已发现线索
- ✅ 记录关键 NPC 的基础状态
- ❌ 不做复杂地图系统
- ❌ 不做长期关系网络

---

### 6. 叙事反馈（DM）

- ✅ 根据世界状态和判定结果生成叙事文本
- ✅ 体现成功 / 失败的差异
- ✅ 渲染基本氛围
- ❌ 不直接修改结构化状态
- ❌ 不凭空创造关键线索和重大结果

## v0.0 完成标准

当系统能够满足以下条件时，视为 v0.0 完成：

- 玩家可以创建角色并开始游戏
- 玩家可以在固定模组中连续输入自然语言行动
- 系统可以稳定完成“解析 → 判定 → 状态更新 → 叙事反馈”闭环
- 系统可连续运行 10 轮以上且无明显逻辑崩坏
- 玩家状态、线索、位置等基础信息能够被正确维护

## 未来可实现的功能：

- [ ]  多玩家
- [ ]  自由世界生成
- [ ]  完整TRPG规则（如COC全套）
- [ ]  长期剧情一致性
- [ ]  NPC复杂人格系统
- [ ]  战斗系统
- [ ]  开放地图探索
- [ ]  UI（只做CLI）

# 技术设计

# 一、V0.0总原则

v0.0 里，系统需遵守这条规则：

> **只有 World State Manager / Rules Engine 有权修改结构化状态。**
> 
> - PM 负责解析和调度。
> - DM 只负责生成面向玩家的叙事文本。

这样做的好处是：

- 不容易出现“LLM 胡乱改状态”
- 方便 debug
- 每一步错误都能定位到模块

---

# 二、v0.0 总体数据流

若本回合需检定：

```
玩家输入
→ PM Agent 解析意图
→ Rules Engine 判断/执行检定
→ World State 更新
→ DM Agent 生成叙事反馈
→ 返回给玩家
```

若本回合不需要检定，则变成：

```
玩家输入
→ PM Agent 解析意图
→ 直接生成状态变更建议
→ World State 更新
→ DM Agent 生成叙事反馈
→ 返回给玩家
```

---

# 三、核心对象

 v0.0 统一使用 6 个核心结构：

1. `PlayerAction`：玩家原始输入
2. `ParsedAction`：PM 解析后的动作
3. `RuleRequest`：发给 Rules 的请求
4. `RuleResult`：Rules 返回的结果
5. `WorldState`：当前世界状态
6. `NarrativeResponse`：最终给玩家看的输出

## 1. 玩家输入：PlayerAction

这是最外层输入，尽量简单。

```json
{
  "session_id": "session_001",
  "turn_id": 1,
  "raw_input": "我想假装成送货员混进庄园",
  "timestamp": "2026-03-20T20:00:00+08:00"
}
```

### 字段说明

- `session_id`：当前游戏会话 ID
- `turn_id`：第几轮
- `raw_input`：玩家自然语言输入
- `timestamp`：时间戳

---

## 2. PM 输出：ParsedAction

这是最关键的结构。PM 的任务不是写小说，而是把玩家的话压成结构化动作。

```json
{
  "action_type": "deception_infiltration",
  "intent": "伪装身份进入目标地点",
  "target": "庄园",
  "method": "假装送货员",
  "requires_check": true,
  "check_type": "charisma",
  "difficulty": 12,
  "preconditions": [
    "玩家当前位于庄园外",
    "庄园门口有守卫"
  ],
  "on_success": [
    "进入庄园外院"
  ],
  "on_failure": [
    "守卫起疑",
    "警惕度上升"
  ],
  "notes": "允许后续触发调查类行动"
}
```

### 字段说明

- `action_type`：动作类型，供程序分流
- `intent`：动作意图的人类可读总结
- `target`：目标对象/地点
- `method`：采用的方法
- `requires_check`：是否需要检定
- `check_type`：使用什么属性
- `difficulty`：难度等级
- `preconditions`：成立前提
- `on_success` / `on_failure`：结果建议
- `notes`：补充说明

---

## 3. Rules Engine输入：RuleRequest

PM 不直接掷骰。它只是把需要判定的请求发给 Rules Engine。

```json
{
  "turn_id": 1,
  "actor_id": "player",
  "action_type": "deception_infiltration",
  "check_type": "charisma",
  "difficulty": 12,
  "player_modifier": 2,
  "context_tags": ["庄园入口", "门卫在场"]
}
```

### 字段说明

- `turn_id`：第几轮
- `actor_id`：谁执行动作
- `action_type`：动作类别
- `check_type`：检定属性
- `difficulty`：目标难度
- `player_modifier`：属性修正值
- `context_tags`：上下文标签，便于记录日志

---

## 4. Rules Engine输出：RuleResult

Rules 只负责“算”，不负责“讲”。

```json
{
  "turn_id": 1,
  "roll": 14,
  "modifier": 2,
  "total": 16,
  "difficulty": 12,
  "outcome": "success",
  "critical": false,
  "mechanical_effects": [
    {
      "type": "npc_alert_change",
      "target": "guard",
      "delta": -1
    },
    {
      "type": "location_unlock",
      "value": "庄园外院"
    }
  ]
}
```

### 字段说明

- `turn_id`：第几轮
- `roll`：骰子原始值
- `modifier`：修正值
- `total`：最终结果
- `difficulty`：难度
- `outcome`：`success / failure / critical_success / critical_failure`
- `critical`：是否临界
- `mechanical_effects`：结构化效果列表

---

## 5. 世界状态：WorldState

这是你整个系统的“真相源”。 v0.0 最小版先这样：

```json
{
  "session_id": "session_001",
  "module_id": "manor_mystery_v0",
  "turn_id": 1,
  "player": {
    "name": "林舟",
    "hp": 10,
    "attributes": {
      "strength": 1,
      "agility": 2,
      "intelligence": 2,
      "charisma": 2
    },
    "inventory": [],
    "status_flags": []
  },
  "world": {
    "current_location": "庄园门口",
    "time_stage": "傍晚",
    "discovered_clues": [],
    "unlocked_locations": ["庄园门口"],
    "chapter": "chapter_1"
  },
  "npcs": {
    "guard": {
      "state": "值守中",
      "alert_level": 2,
      "attitude": "中立"
    }
  },
  "quests": {
    "main_quest": {
      "id": "enter_manor",
      "description": "进入庄园并寻找账本",
      "status": "in_progress"
    }
  },
  "history": {
    "recent_turns": [
      "玩家来到庄园门口"
    ]
  }
}
```

---

## 6. 状态变更请求：StateUpdate

为了避免谁都能乱改状态，单独定义一个中间层。

Rules 和 PM 只提交“变更建议”，由 State Manager 应用。

```json
{
  "turn_id": 1,
  "updates": [
    {
      "op": "set",
      "path": "world.current_location",
      "value": "庄园外院"
    },
    {
      "op": "add",
      "path": "world.unlocked_locations",
      "value": "庄园外院"
    },
    {
      "op": "inc",
      "path": "npcs.guard.alert_level",
      "value": -1
    },
    {
      "op": "append",
      "path": "history.recent_turns",
      "value": "玩家成功伪装成送货员进入庄园外院"
    }
  ]
}
```

### 支持的操作类型

- `set`：直接赋值
- `inc`：数值增减
- `add`：向集合/列表添加唯一项
- `append`：追加记录

这样很适合后面写 Python。

---

## 7. DM 输入：NarrativeContext

DM 不应该直接拿全部原始状态乱发挥。给它“精选后的上下文”。

```json
{
  "player_action": "我想假装成送货员混进庄园",
  "parsed_action": {
    "action_type": "deception_infiltration",
    "target": "庄园",
    "method": "假装送货员"
  },
  "rule_result": {
    "outcome": "success",
    "roll": 14,
    "total": 16,
    "difficulty": 12
  },
  "visible_world_state": {
    "current_location": "庄园外院",
    "nearby_npcs": ["guard"],
    "nearby_objects": ["木箱", "侧门", "石板路"]
  },
  "tone": "悬疑、轻度紧张"
}
```

---

## 8. DM 输出：NarrativeResponse

这是给玩家看的结果，可以把叙事和辅助信息拆开。

```json
{
  "narrative_text": "门卫皱着眉打量了你两秒，视线在木箱和你的脸之间来回游移。最终，他不耐烦地挥了挥手，示意你赶紧进去。你踩过潮湿的石板路，进入了庄园外院。厨房方向传来模糊的争吵声，而主屋侧门虚掩着，像是在等谁。",
  "player_options_hint": [
    "前往厨房查看",
    "靠近主屋侧门",
    "观察周围环境"
  ],
  "important_notice": "你已进入庄园外院。"
}
```

# 四、固定的类型枚举

### 1. 固定 `action_type` 枚举

v0.0 千万不要让动作类型无限发散。先强行定一个小集合。

```
move              移动
observe           观察
investigate       调查
talk              对话
persuade          说服
deceive           欺骗/伪装
stealth           潜行
take_item         拿取物品
use_item          使用物品
attack            攻击
```

### 2. 固定 `check_type` 枚举

v0.0的检定类型也不要太自由：

```
strength          力量检定
agility           敏捷检定
intelligence      智力检定
charisma          魅力检定
none
```

其中 `none` 表示不需要检定。

例如：

- “我看看桌上有什么” → `observe` + `none`
- “我搜索抽屉里的账本” → `investigate` + `intelligence`
- “我翻墙进去” → `move` 或 `stealth` + `agility`
- “我说服门卫放行” → `persuade` + `charisma`

# 五、模块接口

## 1. PM Agent

### 输入

- `PlayerAction`
- 当前 `WorldState`

### 输出

- `ParsedAction`
- 若需要检定，再生成 `RuleRequest`
- 若不需要检定，可生成基础 `StateUpdate`

### 不允许

- 不允许直接改 `WorldState`
- 不允许直接生成最终叙事

---

## 2. Rules Engine

### 输入

- `RuleRequest`
- 当前 `WorldState` 中角色属性部分

### 输出

- `RuleResult`

### 不允许

- 不允许直接写叙事
- 不允许直接修改完整世界状态

---

## 3. World State Manager

### 输入

- 当前 `WorldState`
- `RuleResult`
- `ParsedAction`
- `StateUpdate`

### 输出

- 更新后的 `WorldState`

### 职责

- 应用状态变更
- 维护 recent history
- 保证字段合法

---

## 4. DM Agent

### 输入

- `NarrativeContext`

### 输出

- `NarrativeResponse`

### 不允许

- 不允许新增关键线索
- 不允许修改结构化状态
- 不允许推翻 Rules 结果

---

# 六、完整回合示例

## Step 1 - 玩家输入

```json
{
  "session_id": "session_001",
  "turn_id": 1,
  "raw_input": "我想假装成送货员混进庄园"
}
```

---

## Step 2 - PM 解析

```json
{
  "action_type": "deceive",
  "intent": "伪装身份骗过守卫进入庄园",
  "target": "庄园门卫",
  "method": "假装送货员",
  "requires_check": true,
  "check_type": "charisma",
  "difficulty": 12,
  "preconditions": ["玩家在庄园门口", "门卫在场"],
  "on_success": ["进入庄园外院"],
  "on_failure": ["守卫起疑"]
}
```

---

## Step 3 - Rules 执行

```json
{
  "turn_id": 1,
  "roll": 15,
  "modifier": 2,
  "total": 17,
  "difficulty": 12,
  "outcome": "success",
  "critical": false,
  "mechanical_effects": [
    {
      "type": "location_change",
      "value": "庄园外院"
    },
    {
      "type": "npc_alert_change",
      "target": "guard",
      "delta": -1
    }
  ]
}
```

---

## Step 4 - 状态更新

```json
{
  "turn_id": 1,
  "updates": [
    {
      "op": "set",
      "path": "world.current_location",
      "value": "庄园外院"
    },
    {
      "op": "add",
      "path": "world.unlocked_locations",
      "value": "庄园外院"
    },
    {
      "op": "inc",
      "path": "npcs.guard.alert_level",
      "value": -1
    },
    {
      "op": "append",
      "path": "history.recent_turns",
      "value": "玩家伪装成送货员，成功进入庄园外院"
    }
  ]
}
```

---

## Step 5 DM 输出

```json
{
  "narrative_text": "门卫狐疑地看了你一眼，又低头看了看你手里的木箱。几秒后，他啧了一声，侧身让开了道路。你顺利走进庄园外院，空气里弥漫着潮湿泥土和消毒水混杂的味道。不远处的厨房传来争执声，而主屋侧门半掩着，像是刚有人进去。",
  "player_options_hint": [
    "前往厨房",
    "进入主屋侧门",
    "观察外院环境"
  ],
  "important_notice": "新地点已解锁：庄园外院"
}
```