from typing import Literal, Optional, List
from pydantic import BaseModel, Field

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


class ParsedAction(BaseModel):
    action_type: ActionType = Field(description="动作类型")
    target: Optional[str] = Field(default=None, description="动作目标")
    method: Optional[str] = Field(default=None, description="动作方式")
    requires_check: bool = Field(description="是否需要检定")
    check_type: CheckType = Field(description="检定使用的属性类型")

class NarrativeResponse(BaseModel):
    narrative_text: str = Field(description="叙事文本")
    player_options_hint: List[str] = Field(default_factory=list, description="给玩家的行动提示")
    important_notice: Optional[str] = Field(default=None, description="重要提示")