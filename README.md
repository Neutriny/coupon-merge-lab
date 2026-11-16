# coupon-merge-lab

两种优惠券机制的数学推演与交互式可视化：**合成（merge）** 与 **叠加（stack）**。

纯 Python 计算 + marimo notebook，把「两张券烧成一张」和「多张券同时夹上」
两套规则的边界、上限与最优策略推到极限，并给出可交互的试算工具。

## 两套机制

|      | 合成 (merge)                                             | 叠加 (stack)                            |
| :--: | :------------------------------------------------------: | :-------------------------------------: |
| 作用 | 两张券**烧成一张**                                       | 多张券**同时夹上**                      |
| 公式 | $\max + \operatorname{round}\dfrac{\min(100-\max)}{200}$ | $1-\prod\left(1-\frac{p_i}{100}\right)$ |
| 上限 | **99%**（硬顶，吸收态）                                  | 无上限，可逼近 100%                     |
| 消耗 | 两张券变一张                                             | 券全部保留                              |

券面值下限 **5%**（铸造台只出 5 / 10 / 15 / 25 / 40）。

## 快速开始

```bash
uv sync
marimo edit src/coupon_nb.py   # 交互式 notebook
```

或者在 IPython 里直接算：

```python
import sys; sys.path.insert(0, "src")
from coupon import merge, stack, merge_order, balanced_plan

merge(95, 41)          # 96
stack([95, 41])        # 101.05 -> 实际总折扣 97.05%
print(merge_order([5, 5, 5, 5]))      # 合成顺序
print(balanced_plan([40, 40, 25, 5], purchases=2))   # 兼顾叠加 vs 纯合成
```

## 模块

| 文件 | 内容 |
| --- | --- |
| `src/coupon.py` | 纯计算核心：`merge` / `stack` / `gain` / `chain` / `merge_order` / `balanced_plan` |
| `src/coupon_cli.py` | 交互式外壳：`safe_merge` 把非法参数翻译成中文提示 |
| `src/coupon_chart.py` | plotly 图表工厂，只返回 Figure，不打印 |
| `src/coupon_nb.py` | marimo notebook，5 节可视化讲解 |
| `优惠券合成机制总结.md` | 完整推导与策略结论 |

## 核心结论

1. **叠加永远 ≥ 合成**（单次购买场景），合成是长期投资、叠加是即时消费。
2. 合成收益 $= \dfrac{\min \times (100-\max)}{200}$，与大券剩余空间成正比
   —— 所以**永远优先合最小的两张**。
3. 99% 是吸收态，合成路线应攒 99% 而非追 100%。
4. 真正提升总折扣的是**拆单**：把券分到多次购买，每单取「直接叠加」或
   「先合成再叠加」中更划算者。券数 ≤ 10 时穷举求最优，否则局部搜索。

## 开发

```bash
uv run ruff check src
uv run ruff format --check src
uvx ty check .
```
