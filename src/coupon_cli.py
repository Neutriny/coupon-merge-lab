"""`coupon.merge` 的交互式外壳：参数不合要求时给出中文提示。

`coupon.merge` 是纯函数，参数非法一律返回 None，不便交互式试算。
这里包一层 `safe_merge`，把「为什么合不了」翻译成人话，同时返回结果
和提示，方便在 IPython 里直接看：

    from coupon_cli import safe_merge
    safe_merge(95, 41)    # 正常情况，无提示
    safe_merge(99, 99)    # 提示：99% 已是上限，无法再合成
    safe_merge(0, 50)     # 提示：券面值最低 5%

`explain_merge` 只返回提示字符串（无问题时为空串），适合放进
notebook 单元格直接显示。
"""

from __future__ import annotations

from dataclasses import dataclass

from coupon import MAX_MERGE, MIN_PCT, TIERS, merge

# 非整数参数允许的浮点误差，避免 40.0000001 被当成非法值
_EPS = 1e-9


@dataclass(frozen=True, slots=True)
class MergeReport:
    """一次 `merge` 调用的结果与提示。"""

    result: int | None
    message: str

    @property
    def ok(self) -> bool:
        """参数合法且确实能合成。"""
        return self.result is not None

    def __str__(self) -> str:
        return self.message or f"合成结果：{self.result}%"


def explain_merge(a: float, b: float) -> str:
    """把 `merge(a, b)` 的问题翻译成提示；无问题时返回空串。"""
    for name, v in (("a", a), ("b", b)):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return f"参数 {name} 必须是数值，收到 {type(v).__name__}：{v!r}"
        if v != v or v in (float("inf"), float("-inf")):
            return f"参数 {name} 不能是 NaN / inf：{v!r}"
        if abs(v - round(v)) > _EPS:
            return f"参数 {name} 必须是整数面值，收到 {v!r}"

    left, right = round(a), round(b)
    for name, v in (("a", left), ("b", right)):
        if v > MAX_MERGE:
            return f"{name} = {v}% 超过单张券上限 {MAX_MERGE}%"
        if v < MIN_PCT:
            tiers = " / ".join(map(str, TIERS))
            return (
                f"{name} = {v}% 低于券面值下限 {MIN_PCT}%"
                f"（铸造台只出 {tiers}，没有 {v}% 的券）"
            )

    if merge(left, right) is not None:
        return ""

    big, small = max(left, right), min(left, right)
    if big == small:
        return f"{big}% + {big}% 无法合成：两张券之间已无剩余空间可提升"

    # 面值都在范围内却仍失败：剩余空间不足以让面值至少进 1
    full = small * (100 - big) / 100
    return (
        f"{big}% + {small}% 无法合成：剩余空间只够增加 {full:.2f}%，"
        f"不足 1%，面值提不上去"
    )


def safe_merge(a: float, b: float) -> MergeReport:
    """带提示的 `merge`：参数不合法时 `result` 为 None，`message` 说明原因。"""
    message = explain_merge(a, b)
    return MergeReport(None if message else merge(round(a), round(b)), message)
