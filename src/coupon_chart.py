"""优惠券图表工厂：只返回 plotly Figure，由 marimo 负责渲染/导出。

券面值最低 5（铸造台档位），所以所有矩阵 / 曲线只在 >= 5 的范围取点。
函数本身不做打印，图表可以直接批量调用。
"""

from __future__ import annotations

import itertools

import plotly.graph_objects as go

from coupon import (
    MAX_MERGE,
    MIN_PCT,
    merge,
    plan_by_purchases,
    stack,
)

VALUES = list(range(MIN_PCT, 100))


def result_or_sentinel(a: int, b: int) -> int:
    r = merge(a, b)
    return -1 if r is None else r


def gain_or_sentinel(a: int, b: int) -> int:
    """批量算收益，不打印提示（矩阵里有大量无收益组合）。"""
    r = merge(a, b)
    return -1 if r is None else r - max(a, b)


RESULT = [[result_or_sentinel(a, b) for b in VALUES] for a in VALUES]
GAIN = [[gain_or_sentinel(a, b) for b in VALUES] for a in VALUES]
BEST = max(max(row) for row in GAIN)

LAYOUT = dict(template="plotly_white", legend=dict(orientation="h", y=-0.12))
AXIS_RANGE = [MIN_PCT - 0.5, MAX_MERGE + 0.5]


def fig_heatmap(highlight: tuple[int, int] | None = None) -> go.Figure:
    """合成结果矩阵：颜色 = 合成后面值，灰点 = 合不了。"""
    fig = go.Figure(
        go.Heatmap(
            z=RESULT,
            x=VALUES,
            y=VALUES,
            customdata=GAIN,
            colorscale="Viridis",
            zmin=0,
            zmax=MAX_MERGE,
            colorbar=dict(title="合成后<br>面值", len=0.85),
            hovertemplate=(
                "券 A = %{y}%<br>券 B = %{x}%<br>"
                "合成 → %{z}%<br>收益 +%{customdata}<extra></extra>"
            ),
        )
    )

    bad = [
        (x, y)
        for y, row in zip(VALUES, RESULT, strict=True)
        for x, v in zip(VALUES, row, strict=True)
        if v < 0
    ]
    fig.add_trace(
        go.Scatter(
            x=[p[0] for p in bad],
            y=[p[1] for p in bad],
            mode="markers",
            marker=dict(
                symbol="square", size=4, color="rgba(130,130,130,0.55)"
            ),
            name="合不了 / 无收益",
            hoverinfo="skip",
        )
    )

    markers = [
        (
            (50, 50),
            f"单次最大收益 +{BEST}（50 + 50）",
            f"50% + 50% → 63%<br>单次最大收益 +{BEST}",
        )
    ]
    if highlight:
        markers.append(((highlight[1], highlight[0]), "当前选择", None))
    for (x, y), name, hover in markers:
        current = (y, x) == highlight
        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y],
                mode="markers",
                marker=dict(
                    symbol="x-thin" if current else "star",
                    size=18,
                    color="#d62728" if current else "#ffffff",
                    line=dict(width=3 if current else 1.5, color="#222222"),
                ),
                name=name,
                hovertemplate=hover,
                hoverinfo="skip" if hover is None else "all",
            )
        )

    fig.update_layout(
        title="合成结果矩阵（券面值 5–99）",
        xaxis_title="配对券面值 (%)",
        yaxis_title="主券面值 (%)",
        height=700,
        margin=dict(l=60, r=20, t=70, b=90),
        **LAYOUT,
    )
    fig.update_xaxes(range=AXIS_RANGE, dtick=10)
    fig.update_yaxes(range=AXIS_RANGE, dtick=10, scaleanchor="x")
    return fig


def fig_curves() -> go.Figure:
    """固定主券，看「配对券面值 → 收益」曲线。"""
    fig = go.Figure()
    for n in [10, 20, 40, 62, 75, 92, 95, 98]:
        fig.add_trace(
            go.Scatter(
                x=VALUES,
                y=[gain_or_sentinel(n, m) for m in VALUES],
                mode="lines",
                name=f"主券 {n}%",
                line=dict(width=2, shape="hv"),
                hovertemplate=f"主券 {n}%<br>配对券 %{{x}}%<br>收益 %{{y}}<extra></extra>",
            )
        )

    fig.add_vline(
        x=51,
        line=dict(color="#d62728", dash="dash", width=1),
        annotation_text="98% 主券至少要 51% 配对券",
        annotation_position="top right",
    )
    fig.update_layout(
        title="固定主券时，收益随配对券面值的变化",
        xaxis_title="配对券面值 (%)",
        yaxis_title="合成收益（面值 +N）",
        hovermode="x unified",
        height=580,
        **LAYOUT,
    )
    fig.update_xaxes(range=[MIN_PCT, 100])
    fig.update_yaxes(range=[0, 10])
    return fig


def fig_surface() -> go.Figure:
    """3D 收益曲面。"""
    fig = go.Figure(
        go.Surface(
            z=GAIN,
            x=VALUES,
            y=VALUES,
            colorscale="RdYlBu_r",
            cmin=0,
            cmax=BEST,
            colorbar=dict(title="收益"),
            hovertemplate="券 A = %{y}%<br>券 B = %{x}%<br>收益 +%{z}<extra></extra>",
        )
    )
    fig.update_layout(
        title="合成收益曲面：收益 ∝ 小券 × 大券剩余空间",
        scene=dict(
            xaxis_title="券 B (%)",
            yaxis_title="券 A (%)",
            zaxis_title="收益 (+%)",
            camera=dict(eye=dict(x=1.7, y=-1.5, z=0.9)),
            aspectratio=dict(x=1, y=1, z=0.7),
        ),
        template="plotly_white",
        height=660,
    )
    return fig


def fig_stack_vs_merge() -> go.Figure:
    """对比：同样投入一张 5% 券，「叠加」比「合成」强多少。"""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=VALUES,
            y=[stack([a, MIN_PCT]) for a in VALUES],
            mode="lines",
            name="叠加（乘法，同时夹上 5% 券）",
            line=dict(width=3, color="#2ca02c"),
            hovertemplate="券 %{x}% + 5% 叠加<br>总折扣 %{y:.2f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=VALUES,
            y=[merge(a, MIN_PCT) for a in VALUES],
            mode="lines",
            name="合成（消耗 5% 券）",
            line=dict(width=3, color="#1f77b4", dash="dot"),
            hovertemplate="券 %{x}% 合成 5%<br>得到 %{y}%<extra></extra>",
        )
    )
    fig.update_layout(
        title="叠加 vs 合成：同样投入一张 5% 券，结果差多少",
        xaxis_title="原有大券面值 (%)",
        yaxis_title="最终折扣 (%)",
        hovermode="x unified",
        height=560,
        **LAYOUT,
    )
    fig.update_xaxes(range=[MIN_PCT, 100])
    fig.update_yaxes(range=[0, 100])
    return fig


def fig_stack_decay(k: int = 20) -> go.Figure:
    """叠加的边际效益递减：第 k 张 5% 券带来多少。"""
    totals = [stack([MIN_PCT] * i) for i in range(1, k + 1)]
    deltas = [b - a for a, b in itertools.pairwise([0.0, *totals])]
    xs = list(range(1, k + 1))

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=xs,
            y=deltas,
            marker_color="#9467bd",
            name="该张券的边际贡献",
            hovertemplate="第 %{x} 张 5% 券<br>额外 +%{y:.2f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=totals,
            mode="lines+markers",
            name="累计总折扣",
            yaxis="y2",
            line=dict(color="#d62728", width=2),
            hovertemplate="夹 %{x} 张 5% 券<br>总折扣 %{y:.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        title="叠加的边际递减：每多夹一张 5% 券的收益",
        xaxis_title="累计夹上的券数（每张 5%）",
        yaxis_title="该张券的边际贡献 (%)",
        yaxis2=dict(
            title="累计总折扣 (%)", overlaying="y", side="right", range=[0, 100]
        ),
        height=540,
        **LAYOUT,
    )
    return fig


def fig_purchase_curve(pcts: list[int], exact: bool | None = None) -> go.Figure:
    """不同购买次数下的总折扣：兼顾叠加 vs 纯合成。"""
    rows = plan_by_purchases(pcts, exact=exact)
    xs = [n for n, _ in rows]
    mixed = [r.plan.total for _, r in rows]
    pure = [r.pure_merge.total for _, r in rows]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=mixed,
            mode="lines+markers",
            name="兼顾叠加",
            line=dict(color="#2ca02c", width=2),
            hovertemplate="%{x} 单<br>总折扣 %{y:.2f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=pure,
            mode="lines+markers",
            name="纯合成",
            line=dict(color="#d62728", width=2, dash="dash"),
            hovertemplate="%{x} 单<br>总折扣 %{y:.2f}%<extra></extra>",
        )
    )
    best_n = max(rows, key=lambda kv: kv[1].plan.total)[0]
    fig.add_vline(
        x=best_n,
        line=dict(color="#7f7f7f", dash="dot"),
        annotation_text=f"最优 {best_n} 单",
    )
    fig.update_layout(
        title=f"券 {sorted(pcts)}：拆几单最划算",
        xaxis_title="购买次数",
        yaxis_title="总折扣 (%)",
        height=480,
        **LAYOUT,
    )
    return fig
