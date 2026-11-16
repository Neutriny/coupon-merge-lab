"""优惠券的合成（merge）与叠加（stack）两套机制。

纯计算模块：参数非法时返回 None / -1，不做任何打印；
需要带提示的交互式调用请看 `coupon_cli.py`。

详见 `优惠券合成机制总结.md`。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

NL = chr(10)
MIN_PCT = 5
MAX_MERGE = 99
TIERS: list[int] = [5, 10, 15, 25, 40]


def js_round(x: float) -> int:
    """.5 向 +inf 进位，与 Python 的银行家舍入区分开。"""
    return math.floor(x + 0.5)


def merge(a: int, b: int) -> int | None:
    """两张券合成的结果；合不了时返回 None。

    结果 = max + round(min * (100 - max) / 200)，上限 99。
    """
    n, m = max(a, b), min(a, b)
    if n >= 100:
        return None
    full = m * (100 - n) / 100
    guard = math.ceil(n + full - 1e-9) - 1
    r = min(MAX_MERGE, guard, max(n + 1, js_round(n + full / 2)))
    return r if r > n else None


def gain(a: int, b: int) -> int:
    """合成收益（面值增量）；合不了记 -1，便于画图取最小值。"""
    r = merge(a, b)
    return -1 if r is None else r - max(a, b)


def required_partner(t: int) -> int | None:
    """主券 t 继续提升所需的最小配对券；无解返回 None。"""
    return next(
        (m for m in range(MIN_PCT, t + 1) if merge(t, m) is not None),
        None,
    )


def chain(start: int = MIN_PCT) -> list[int]:
    """同值对合链：每步两张同值券合成一张更高券。"""
    path = [start]
    while (r := merge(path[-1], path[-1])) is not None:
        path.append(r)
    return path


@dataclass(frozen=True, slots=True)
class MergeStep:
    """一次合成：消耗 a、b，得到 result。"""

    a: int
    b: int
    result: int

    def __str__(self) -> str:
        return f"{self.a} + {self.b} -> {self.result}"


@dataclass(frozen=True, slots=True)
class MergePlan:
    """一组券的合成顺序与最终结果。"""

    steps: list[MergeStep]
    leftover: list[int]

    def __str__(self) -> str:
        lines = [f"{i:>2}. {step}" for i, step in enumerate(self.steps, 1)]
        lines = lines or ["（无需合成）"]
        lines.append(f"剩余：{sorted(self.leftover)}")
        return NL.join(lines)


def _best_pair(pool: list[int]) -> int | None:
    """返回最该合成的那一对里靠前的下标（pool 已升序）。

    优先 min+min：相邻两券按面值升序扫描，第一个能合成的就是
    面值最小的一对，符合「永远优先合最小的两张」。
    """
    n = len(pool)
    for i in range(n - 1):
        if merge(pool[i], pool[i + 1]) is not None:
            return i
    best: tuple[int, int] | None = None
    for i in range(n):
        for j in range(i + 1, n):
            if merge(pool[i], pool[j]) is None:
                continue
            key = (pool[i], pool[j])
            if best is None or key < best:
                best = key
    return None if best is None else pool.index(best[0])


def merge_order(pcts: list[int]) -> MergePlan:
    """给出把一组券依次合成的顺序（小券优先的贪心）。

    每步都在可合成的组合里挑面值最小的一对，因为
    gain = 小 × (100 - 大) / 200，拿大券当底座会浪费小券的潜力
    （见总结文档 6.1）。合不了或只剩一张时留作剩余。

    >>> print(merge_order([5, 5]))
     1. 5 + 5 -> 7
    剩余：[7]
    """
    pool = sorted(pcts)
    steps: list[MergeStep] = []
    while len(pool) > 1 and (i := _best_pair(pool)) is not None:
        a, b = pool[i], pool[i + 1]
        r = merge(a, b)
        assert r is not None  # _best_pair 只返回合得了的相邻下标
        steps.append(MergeStep(a, b, r))
        del pool[i + 1], pool[i]
        pool.append(r)
        pool.sort()
    return MergePlan(steps, pool)


@dataclass(frozen=True, slots=True)
class Purchase:
    """一次购买用掉的券，以及是否先合成。

    一单内的最优用法只有两种：直接叠加全部券，或先合到顶再叠加。
    这里记录更划算的那一种。
    """

    coupons: list[int]
    merge_steps: list[MergeStep] = field(default_factory=list)
    used: list[int] = field(default_factory=list)

    @property
    def discount(self) -> float:
        return stack(self.used)

    @property
    def merged(self) -> bool:
        return bool(self.merge_steps)

    def __str__(self) -> str:
        return f"{self.coupons} -> 用 {self.used} -> {self.discount:.2f}%"


def _make_purchase(cards: list[int]) -> Purchase:
    """一单的最优用法：叠加 vs 先合成再叠加，取折扣更高者。"""
    if not cards:
        return Purchase([], [], [])
    cards = sorted(cards)
    plan = merge_order(cards)
    via_merge = stack(plan.leftover)
    via_stack = stack(cards)
    if via_merge > via_stack:
        return Purchase(cards, plan.steps, plan.leftover)
    return Purchase(cards, [], cards)


@dataclass(frozen=True, slots=True)
class BatchPlan:
    """把一组券分配到多次购买里的方案。"""

    purchases: list[Purchase]

    @property
    def total(self) -> float:
        return sum(p.discount for p in self.purchases)

    def __str__(self) -> str:
        lines = []
        for i, p in enumerate(self.purchases, 1):
            tag = "先合成" if p.merged else "直接叠加"
            lines.append(
                f"  第 {i} 单（{tag}）：{p.coupons} -> {p.discount:.2f}%"
            )
        lines.append(f"  合计：{self.total:.2f}%")
        return NL.join(lines)


def stack(pcts: list[int]) -> float:
    """多张券同时夹上时的总折扣：1 - Π(1 - p/100)，乘法叠加。"""
    remaining = math.prod(max(0.0, 1 - p / 100) for p in pcts)
    return (1 - remaining) * 100


@dataclass(frozen=True, slots=True)
class StrategyReport:
    """兼顾叠加的方案与纯合成方案的对比。"""

    plan: BatchPlan
    pure_merge: BatchPlan

    @property
    def gain(self) -> float:
        """相比纯合成多出来的总折扣（百分点）。"""
        return self.plan.total - self.pure_merge.total

    def __str__(self) -> str:
        return NL.join(
            [
                "兼顾叠加：",
                str(self.plan),
                "",
                "纯合成：",
                str(self.pure_merge),
                "",
                f"差值：{self.gain:+.2f} 个百分点",
            ]
        )


def _spread(pcts: list[int], purchases: int) -> list[list[int]]:
    """把券摊到各单：大券分散开，避免挤在同一单里浪费剩余空间。"""
    buckets: list[list[int]] = [[] for _ in range(purchases)]
    for i, v in enumerate(sorted(pcts, reverse=True)):
        buckets[i % purchases].append(v)
    return [b for b in buckets if b]


def _improve(buckets: list[list[int]], rounds: int = 200) -> list[list[int]]:
    """局部搜索：把一张券挪到另一单，总折扣变高就接受。"""
    best = sum(_make_purchase(b).discount for b in buckets)
    for _ in range(rounds):
        improved = False
        for src in range(len(buckets)):
            for card in list(buckets[src]):
                if card not in buckets[src]:
                    continue
                for dst in range(len(buckets)):
                    if dst == src:
                        continue
                    trial = [list(b) for b in buckets]
                    trial[src].remove(card)
                    trial[dst].append(card)
                    total = sum(_make_purchase(b).discount for b in trial)
                    if total > best + 1e-9:
                        buckets, best, improved = trial, total, True
                        break
                if improved:
                    break
            if improved:
                break
        if not improved:
            break
    return buckets


def _partitions(cards: list[int], max_parts: int):
    """枚举把 cards 分成至多 max_parts 个非空桶的所有方案。

    用受限增长串（restricted growth string）枚举集合划分，
    避免把同一分组的不同排列重复枚举。
    """
    n = len(cards)
    labels = [0] * n

    def rec(i: int, used: int):
        if i == n:
            buckets: list[list[int]] = [[] for _ in range(used)]
            for card, k in zip(cards, labels, strict=True):
                buckets[k].append(card)
            yield buckets
            return
        for k in range(min(used + 1, max_parts)):
            labels[i] = k
            yield from rec(i + 1, max(used, k + 1))

    yield from rec(0, 0)


def optimal_plan(pcts: list[int], purchases: int = 1) -> BatchPlan:
    """穷举最优：把券分成至多 purchases 组，使各单折扣之和最大。

    分组数是 2 的幂级增长（贝尔数），券数超过 EXACT_LIMIT 时不宜穷举，
    请改用 balanced_plan 的启发式结果。
    """
    cards = sorted(pcts)
    purchases = max(1, purchases)
    best: list[list[int]] = []
    best_total = -1.0
    for buckets in _partitions(cards, purchases):
        total = sum(_make_purchase(b).discount for b in buckets)
        if total > best_total + 1e-9:
            best, best_total = buckets, total
    if not best:
        return BatchPlan([])
    return BatchPlan([_make_purchase(b) for b in best])


# 穷举代价按贝尔数增长：10 张券约 0.1s，12 张约 1.3s，故取 10 作为交互上限
EXACT_LIMIT = 10


def balanced_plan(
    pcts: list[int],
    purchases: int = 1,
    *,
    exact: bool | None = None,
) -> StrategyReport:
    """兼顾叠加的方案：不一路合成到顶，而是分到多单里尽量多占折扣。

    单次购买时叠加永远 >= 合成（文档第 5 节），所以价值来自拆分：
    每单可以「直接叠加」或「先合成再叠加」，取更划算者，目标是各单折扣之和最大。
    与「合到顶再一次性使用」的纯合成方案做对比。

    exact 为 None 时，券数 <= EXACT_LIMIT 用穷举求最优，否则用局部搜索。

    >>> balanced_plan([5, 5], 2).gain > 0
    True
    """
    pcts = list(pcts)
    if not pcts:
        return StrategyReport(BatchPlan([]), BatchPlan([]))

    use_exact = len(pcts) <= EXACT_LIMIT if exact is None else exact
    if use_exact:
        plan = optimal_plan(pcts, purchases)
    else:
        buckets = _improve(_spread(pcts, max(1, purchases)))
        plan = BatchPlan([_make_purchase(b) for b in buckets if b])

    # 纯合成对照：忠实反映「一路合到顶」路线，即使单看折扣不如叠加
    merged = merge_order(pcts)
    pure = BatchPlan([Purchase(sorted(pcts), merged.steps, merged.leftover)])
    return StrategyReport(plan, pure)


def plan_by_purchases(
    pcts: list[int],
    max_purchases: int | None = None,
    *,
    exact: bool | None = None,
) -> list[tuple[int, StrategyReport]]:
    """对 1..max_purchases 次购买分别求方案，用于画收益曲线。"""
    pcts = list(pcts)
    upper = max_purchases or max(1, len(pcts))
    return [
        (n, balanced_plan(pcts, n, exact=exact)) for n in range(1, upper + 1)
    ]


def price_after(base: float, pcts: list[int]) -> int:
    """叠加折扣作用到价格上，至少保留 1。"""
    return max(1, math.floor(base * (1 - stack(pcts) / 100)))
