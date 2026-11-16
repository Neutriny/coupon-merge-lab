import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", auto_download=["html"])


@app.cell(hide_code=True)
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))

    import coupon_chart as cc
    from coupon import MIN_PCT, balanced_plan, merge_order, stack
    from coupon_cli import safe_merge

    return MIN_PCT, balanced_plan, cc, merge_order, safe_merge, stack


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 优惠券：合成 vs 叠加

    这是**两套完全不同的机制**，作用在不同阶段：

    |      | 合成 (merge)                                             | 叠加 (stack)                            |
    | :--: | :------------------------------------------------------: | :-------------------------------------: |
    | 作用 | 两张券**烧成一张**                                       | 多张券**同时夹上**                      |
    | 公式 | $\max + \operatorname{round}\dfrac{\min(100-\max)}{200}$ | $1-\prod\left(1-\frac{p_i}{100}\right)$ |
    | 上限 | **99%**（硬顶）                                          | 可逼近 100%（$n$ 张 99% → 99.99%）      |
    | 消耗 | 两张券变一张                                             | 券全部保留，只影响本次购买              |

    > 券面值最低 **5%**（铸造台只出 5 / 10 / 15 / 25 / 40），不存在 1% 的券。
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. 叠加：纯乘法，边际递减

    总折扣 = $1-\prod(1-p_i/100)$，面板显示时四舍五入。每多夹一张，总折扣只增加
    $(100-\text{当前总折扣}) \times p/100$。
    """)
    return


@app.cell
def _(cc):
    cc.fig_stack_vs_merge()
    return


@app.cell
def _(cc):
    cc.fig_stack_decay()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. 合成：面对面值矩阵

    收益 = $\dfrac{\min \times (100-\max)}{200}$，与**大券剩余空间**成正比。
    99% 是吸收态：`99 + 99` 直接合不了。
    """)
    return


@app.cell
def _(cc):
    cc.fig_heatmap()
    return


@app.cell
def _(cc):
    cc.fig_curves()
    return


@app.cell
def _(cc):
    cc.fig_surface()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. 计算器：合成 or 叠加

    调整两张券的面值，同时算出「合成」和「叠加」两种结果。
    """)
    return


@app.cell
def _(mo):
    a_slider = mo.ui.slider(5, 99, value=95, label="券 A (%)", step=1)
    b_slider = mo.ui.slider(5, 99, value=41, label="券 B (%)", step=1)
    mo.hstack([a_slider, b_slider], justify="start")
    return a_slider, b_slider


@app.cell
def _(a_slider, b_slider, mo, safe_merge, stack):
    _a, _b = a_slider.value, b_slider.value
    _report = safe_merge(_a, _b)
    _merged = _report.result
    _stacked = stack([_a, _b])

    if _merged is None:
        _merge_row = f"| 合成 | {_report.message} |"
        _verdict = "合成这条路走不通，只能叠加。"
    else:
        _merge_row = f"| 合成 | **{_merged}%**（消耗掉一张券） |"
        _verdict = (
            f"叠加比合成多 **{_stacked - _merged:.2f}%**，且两张券都还在手里。"
        )

    mo.md(f"""
    | 方式 | 结果 |
    | :--: | :-: |
    {_merge_row}
    | 叠加 | **{_stacked:.2f}%**（100 元付 {100 - _stacked:.2f} 元） |

    {_verdict}
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. 多券合成顺序

    输入一组券面值，按「永远优先合最小的两张」给出合成顺序。
    """)
    return


@app.cell
def _(mo):
    coupons_input = mo.ui.text(
        value="5, 5, 5, 5, 40, 25",
        label="券面值（逗号分隔）",
        full_width=True,
    )
    coupons_input
    return (coupons_input,)


@app.cell
def _(MIN_PCT, coupons_input, merge_order, mo):
    _raw = [
        s
        for s in coupons_input.value.replace("，", ",").split(",")
        if s.strip()
    ]
    _bad = []
    _vals = []
    for _s in _raw:
        try:
            _vals.append(int(_s.strip()))
        except ValueError:
            _bad.append(_s.strip())

    _out_of_range = [v for v in _vals if not MIN_PCT <= v <= 99]

    if not _raw:
        _out = mo.md("请输入至少一张券。")
    else:
        _problems = []
        if _bad:
            _problems.append(f"以下输入不是整数面值：**{_bad}**")
        if _out_of_range:
            _problems.append(
                f"这些面值超出了 {MIN_PCT}% ~ 99% 的范围：**{_out_of_range}**"
            )

        if _problems:
            _out = mo.md(chr(10).join(_problems))
        else:
            _plan = merge_order(_vals)
            _rows = (
                chr(10).join(
                    f"| {i} | {s.a}% + {s.b}% | **{s.result}%** |"
                    for i, s in enumerate(_plan.steps, 1)
                )
                or "| — | 无需合成 | — |"
            )
            _out = mo.md(f"""
    | 步数 | 操作 | 结果 |
    | :--: | :--- | :--: |
    {_rows}

    剩余券：**{_plan.leftover}**（共 {len(_vals)} 张 → {len(_plan.leftover)} 张）
    """)
    _out
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. 兼顾叠加：拆分 vs 纯合成

    单次购买时叠加永远 >= 合成，所以真正的价值在**拆分到多单**：
    每单可「直接叠加」或「先合成再叠加」，目标是各单折扣之和最大。
    """)
    return


@app.cell
def _(mo):
    plan_input = mo.ui.text(
        value="40, 40, 25, 5",
        label="券面值（逗号分隔）",
        full_width=True,
    )
    plan_count = mo.ui.slider(1, 5, value=2, label="购买次数", step=1)
    plan_exact = mo.ui.checkbox(value=True, label="穷举最优（券数少时）")
    mo.hstack([plan_input, plan_count, plan_exact], justify="start")
    return plan_count, plan_exact, plan_input


@app.cell
def _(MIN_PCT, balanced_plan, mo, plan_count, plan_exact, plan_input):
    _raw = [
        s for s in plan_input.value.replace("，", ",").split(",") if s.strip()
    ]
    _bad = []
    _vals = []
    for _s in _raw:
        try:
            _vals.append(int(_s.strip()))
        except ValueError:
            _bad.append(_s.strip())

    _out_of_range = [v for v in _vals if not MIN_PCT <= v <= 99]

    if not _raw:
        _out = mo.md("请输入至少一张券。")
    else:
        _problems = []
        if _bad:
            _problems.append(f"以下输入不是整数面值：**{_bad}**")
        if _out_of_range:
            _problems.append(
                f"这些面值超出了 {MIN_PCT}% ~ 99% 的范围：**{_out_of_range}**"
            )

        if _problems:
            _out = mo.md(chr(10).join(_problems))
        else:
            _rep = balanced_plan(
                _vals, plan_count.value, exact=plan_exact.value
            )
            _rows = (
                chr(10).join(
                    f"| {i} | `{_p.coupons}` | {_p.discount:.2f}% |"
                    for i, _p in enumerate(_rep.plan.purchases, 1)
                )
                or "| — | 无需用券 | — |"
            )
            _out = mo.md(f"""
    | 单 | 用券 | 折扣 |
    | :-: | :-- | :-: |
    {_rows}

    | 策略 | 总折扣 |
    | :-- | :-: |
    | 兼顾叠加 | **{_rep.plan.total:.2f}%** |
    | 纯合成 | {_rep.pure_merge.total:.2f}% |

    兼顾叠加比纯合成多 **{_rep.gain:.2f}** 个百分点。
    """)
    _out
    return


@app.cell
def _(MIN_PCT, cc, plan_exact, plan_input):
    _cv = []
    for _s in plan_input.value.replace("，", ",").split(","):
        if _s.strip().lstrip("-").isdigit():
            _v = int(_s.strip())
            if MIN_PCT <= _v <= 99:
                _cv.append(_v)
    cc.fig_purchase_curve(_cv, exact=plan_exact.value) if _cv else None
    return


if __name__ == "__main__":
    app.run()
