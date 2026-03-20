"""
v0.0 核心数据结构（与 README「三、核心对象」对齐）。
PM / Rules / WorldState / DM 之间通过 Pydantic 模型传递，减少字段漂移。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# --- README「四、固定的类型枚举」---

ActionType = Literal[
    "move",
    "observe",
    "investigate",
    "talk",
    "persuade",
    "deceive",
    "stealth",
    "take_item",
    "use_item",
    "attack",
]

CheckType = Literal[
    "strength",
    "agility",
    "intelligence",
    "charisma",
    "none",
]


class PlayerAction(BaseModel):
    """玩家原始输入（最外层）。"""

    session_id: str = Field(description="会话 ID")
    turn_id: int = Field(ge=0, description="当前回合序号")
    raw_input: str = Field(description="自然语言行动")
    timestamp: Optional[str] = Field(
        default=None,
        description="ISO8601 时间戳；未传则由调用方在日志中补全",
    )

    @classmethod
    def with_now(cls, session_id: str, turn_id: int, raw_input: str) -> "PlayerAction":
        """生成带 UTC 时间戳的 PlayerAction，便于回溯。"""
        ts = datetime.now(timezone.utc).isoformat()
        return cls(session_id=session_id, turn_id=turn_id, raw_input=raw_input, timestamp=ts)


class ParsedAction(BaseModel):
    """
    PM 解析结果：把自然语言压成结构化动作。
    扩展字段供 LLM 输出；程序侧仅用必填项即可跑通闭环。
    """

    model_config = ConfigDict(extra="ignore")

    action_type: ActionType = Field(description="动作类型")
    intent: Optional[str] = Field(default=None, description="意图简述")
    target: Optional[str] = Field(default=None, description="目标对象/地点")
    method: Optional[str] = Field(default=None, description="采用的方法")
    requires_check: bool = Field(description="是否需要检定")
    check_type: CheckType = Field(description="检定属性；无需检定为 none")
    difficulty: Optional[int] = Field(
        default=None,
        ge=1,
        le=30,
        description="建议 DC；未给出时由 Rules Engine 按动作类型推断",
    )
    preconditions: List[str] = Field(default_factory=list)
    on_success: List[str] = Field(default_factory=list)
    on_failure: List[str] = Field(default_factory=list)
    notes: Optional[str] = Field(default=None)

    @field_validator("difficulty", mode="before")
    @classmethod
    def _coerce_difficulty(cls, v: object) -> Optional[int]:
        if v is None or v == "":
            return None
        return int(v)  # type: ignore[arg-type]

    @field_validator("preconditions", "on_success", "on_failure", mode="before")
    @classmethod
    def _coerce_str_list(cls, v: object) -> List[str]:
        """LLM 有时输出单个字符串，统一为字符串列表以便存档与展示。"""
        if v is None:
            return []
        if isinstance(v, str):
            s = v.strip()
            return [s] if s else []
        if isinstance(v, list):
            return [str(x) for x in v]
        return [str(v)]


# RuleResult.mechanical_effects 中单条效果：type 分流，其余键随类型变化
MechanicalEffect = Dict[str, Any]


class RuleResult(BaseModel):
    """Rules 只负责「算」，叙事由 DM 负责。"""

    turn_id: int
    roll: Optional[int] = None
    modifier: int = 0
    total: Optional[int] = None
    difficulty: int
    outcome: Literal[
        "success",
        "failure",
        "critical_success",
        "critical_failure",
        "none",
    ]
    critical: bool = Field(description="是否为天然 1/20 的临界掷骰")
    mechanical_effects: List[MechanicalEffect] = Field(default_factory=list)


class StateUpdateOp(BaseModel):
    """与 README StateUpdate 对齐的中间表示；当前由 mechanical_effects 驱动等效更新。"""

    op: Literal["set", "inc", "add", "append"]
    path: str
    value: Any


class StateUpdate(BaseModel):
    turn_id: int
    updates: List[StateUpdateOp] = Field(default_factory=list)


class NarrativeResponse(BaseModel):
    """DM 面向玩家的输出。"""

    model_config = ConfigDict(extra="ignore")

    narrative_text: str = Field(description="叙事文本")
    player_options_hint: List[str] = Field(default_factory=list, description="2~3 条可执行建议")
    important_notice: Optional[str] = Field(default=None, description="规则或进度层面的重要提示")
