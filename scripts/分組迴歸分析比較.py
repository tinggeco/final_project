# -*- coding: utf-8 -*-
"""
對比三組迴歸結果：
  1：全時段（8-16點，含8點與12點）
  2：排除8點（9-16點，含12點）
  3：排除8點＋12點（9-11點、13-16點）

輸出：
  F1_regression_comparison_scatter.png  三組迴歸線並排散點圖（2x2 子圖×3組）
  F2_slope_comparison_bar.png           三組斜率對比長條圖
  regression_3groups_summary.csv        三組迴歸統計摘要
"""

import pandas as pd
import numpy as np
import os
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# 基本資料設定

BUILDINGS         = ["新生", "博雅", "共同", "普通"]
BASE_OUTPUT_DIR   = "output"
FIGURE_OUTPUT_DIR = os.path.join(BASE_OUTPUT_DIR, "figures_comparison")

PALETTE = {
    "新生": "#8172B2",
    "博雅": "#55A868",
    "共同": "#4C72B0",
    "普通": "#C44E52"
}

# 三組分析的小時範圍定義
GROUPS = {
    "全時段":         list(range(8, 17)),           # 8-16
    "排除8點":        list(range(9, 17)),            # 9-16
    "排除8點＋12點":  [h for h in range(9, 17) if h != 12],  # 9-11, 13-16
}
GROUP_COLORS = {
    "全時段":        "#999999",
    "排除8點":       "#ff7f0e",
    "排除8點＋12點": "#2ca02c",
}

os.makedirs(FIGURE_OUTPUT_DIR, exist_ok=True)
plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei"]
plt.rcParams["axes.unicode_minus"] = False


# 資料載入與處理，同教學館用電效率分析.py，只是稍微調整，不重複註解了。

def load_data(building_name, data_type):
    keyword_map = {
        "power": f"{building_name}_扣除星期六基礎功率_0700_1800",
        "class": f"{building_name}_classroom_usage_day"
    }
    path = os.path.join(BASE_OUTPUT_DIR, f"{keyword_map[data_type]}.csv")
    if not os.path.exists(path):
        print(f"警告: 找不到檔案 {path}")
        return None
    return pd.read_csv(path, encoding="utf-8-sig")


def melt_classroom_data(df_cls):
    sem_col  = '學年度學期'
    day_col  = '星期'
    time_cols = [c for c in df_cls.columns if '~' in str(c)]
    if not all([sem_col, day_col, time_cols]):
        raise ValueError("課堂數資料缺少必要欄位")

    df_long = df_cls.melt(
        id_vars=[sem_col, day_col], value_vars=time_cols,
        var_name='時間區間', value_name='課堂數'
    ).rename(columns={sem_col: '年度學期', day_col: '星期'})

    df_long['年度學期'] = df_long['年度學期'].astype(str).str.strip().apply(
        lambda x: f'{x[:3]}-{x[3]}' if len(x) == 4 and '-' not in x else x
    )
    df_long['星期']     = df_long['星期'].astype(str).str.strip()
    df_long['時間區間'] = df_long['時間區間'].astype(str).str.strip()
    df_long['課堂數']   = pd.to_numeric(df_long['課堂數'], errors='coerce')
    return df_long


def get_merged_data_for_building(building):
    print(f"-- 正在處理: {building}")
    df_power = load_data(building, "power")
    df_class = load_data(building, "class")
    if df_power is None or df_class is None:
        return None

    df_power.columns = df_power.columns.str.strip()
    df_class.columns = df_class.columns.str.strip()
    df_class_long = melt_classroom_data(df_class)

    for df in [df_power, df_class_long]:
        df['年度學期'] = df['年度學期'].astype(str).str.strip()
        df['星期']     = df['星期'].astype(str).str.strip()
        df['時間區間'] = df['時間區間'].astype(str).str.strip()

    merged = pd.merge(
        df_power[['年度學期', '星期', '時間區間', '扣除基礎後功率_kW']],
        df_class_long,
        on=['年度學期', '星期', '時間區間'], how='inner'
    )
    merged['建築'] = building
    # 從時間區間解析小時
    merged['小時'] = (merged['時間區間'].str.split('~').str[0].str.split(':').str[0].astype(int))
    return merged


# 迴歸計算
def run_regression(df, building, group_name, hours):
    # 對單棟單組跑迴歸，回傳統計結果
    # 篩選出該建築、該組定義的小時，並去除課堂數或功率為NaN的資料點
    sub = df[(df['建築'] == building) & (df['小時'].isin(hours))].dropna(
        subset=['課堂數', '扣除基礎後功率_kW']
    )
    x = sub['課堂數'].values.astype(float)
    y = sub['扣除基礎後功率_kW'].values.astype(float)

    # 用np.isfinite() 是檢查每個值是否為有限數字
    mask = np.isfinite(x) & np.isfinite(y)
    # OK後才進行後續篩選
    x, y = x[mask], y[mask]

    # 課堂數小於2的話就沒辦法跑迴歸了，直接回傳None
    if len(x) < 2:
        return None

    slope, intercept, r, p, se = stats.linregress(x, y)
    return {
        "組別":   group_name,
        "建築":   building,
        "斜率":   round(slope, 4),
        "截距":   round(intercept, 3),
        "R²":     round(r**2, 4),
        "p值":    f"{p:.2e}",
        "樣本數": len(x),
        # 保留浮點數供繪圖用
        "_slope": slope,
        "_intercept": intercept,
        "_r2":    r**2,
        "_x":     x,
        "_y":     y,
    }



# 圖1：散點＋迴歸線並排（3×2x2）
def plot_scatter_comparison(all_results):
    """
    3 列（三組）× 4 欄（四棟）的大圖，
    每格散點圖疊迴歸線，標示斜率與 R²。
    """
    group_names = list(GROUPS.keys()) # 取出三組的名稱，包含"全時段"、"排除8點"、"排除8點＋12點"
    n_groups    = len(group_names)
    n_buildings = len(BUILDINGS)

    fig, axes = plt.subplots(n_groups, n_buildings,figsize=(20, 14), sharey=False) # 3x4的子圖，大小20x14吋，y軸不共用

    fig.suptitle("三組迴歸對比：課堂數 vs 扣除基礎後功率",fontsize=16, fontweight='bold', y=0.99)

    # 直接用enumerate，就不用寫計數器了，row會從0到2，col會從0到3，對應到子圖的位置
    for row, group_name in enumerate(group_names):
        for col, building in enumerate(BUILDINGS):
            ax  = axes[row][col]
            res = all_results.get((group_name, building))
            color = PALETTE.get(building)

            if res is None:
                ax.text(0.5, 0.5, '無資料', ha='center', va='center')
            else:
                x, y = res['_x'], res['_y']
                ax.scatter(x, y, alpha=0.25, s=15, color=color)

                x_line = np.linspace(x.min(), x.max(), 100)
                y_line = res['_slope'] * x_line + res['_intercept']
                ax.plot(x_line, y_line,
                        color=GROUP_COLORS[group_name], linewidth=2)

                ax.text(0.05, 0.93,
                        f"斜率={res['_slope']:.2f}\nR²={res['_r2']:.3f}",
                        transform=ax.transAxes, fontsize=9,
                        va='top', color=GROUP_COLORS[group_name],
                        bbox=dict(boxstyle='round,pad=0.2',
                                  facecolor='white', alpha=0.7))

            # 標題與軸標
            if row == 0:
                ax.set_title(f"{building}館", fontsize=12, fontweight='bold')
            if col == 0:
                ax.set_ylabel(f"{group_name}\n功率 (kW)", fontsize=10)
            if row == n_groups - 1:
                ax.set_xlabel("課堂數 (堂)", fontsize=10)

            ax.grid(True, linestyle='--', alpha=0.4)
    
    # 手動建立圖例，因為不可能每張子圖都放一個圖例，會太亂了，所以統一放在整體圖的下方
    legend_patches = [
        mpatches.Patch(color=GROUP_COLORS[g], label=g) for g in group_names
    ]
    fig.legend(handles=legend_patches, loc='lower center',
               ncol=3, fontsize=11, bbox_to_anchor=(0.5, 0.01))

    plt.tight_layout(rect=[0, 0.05, 1, 0.98])
    out = os.path.join(FIGURE_OUTPUT_DIR, "三組別迴歸分析比較圖.png")
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f">> 圖表儲存：{out}")


# 圖2：斜率對比長條圖

def plot_slope_bar(all_results):
    """
    四棟並排，每棟三組長條，直接看排除8點/12點後斜率的變化量。
    """
    group_names = list(GROUPS.keys())
    x = np.arange(len(BUILDINGS))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 6))

    for i, group_name in enumerate(group_names):
        slopes = []
        for building in BUILDINGS:
            res = all_results.get((group_name, building))
            slopes.append(res['_slope'] if res else 0)

        bars = ax.bar(x + i * width, slopes, width,
                      label=group_name,
                      color=GROUP_COLORS[group_name],
                      alpha=0.85, edgecolor='white')

        # 在長條頂端標數值
        for bar, val in zip(bars, slopes):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05, # 出現位置
                    f"{val:.2f}",
                    ha='center', va='bottom', fontsize=9)

    ax.set_xticks(x + width)
    ax.set_xticklabels([f"{b}館" for b in BUILDINGS], fontsize=12)
    ax.set_ylabel("迴歸斜率 (kW/堂)", fontsize=12)
    ax.set_title("三組迴歸斜率對比", fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
    ax.grid(True, axis='y', linestyle='--', alpha=0.4)

    plt.tight_layout()
    out = os.path.join(FIGURE_OUTPUT_DIR, "三組別迴歸斜率對比圖.png")
    plt.savefig(out, dpi=300)
    plt.close(fig)
    print(f">> 圖表儲存：{out}")


# =============================================================================
# 6. 主程式
# =============================================================================

if __name__ == "__main__":

    # 呼叫get_merged_data_for_building處理每個建築的資料，回傳合併後的DataFrame
    dfs = [get_merged_data_for_building(b) for b in BUILDINGS] 
    df_all = pd.concat([d for d in dfs if d is not None], ignore_index=True)
    print(f"資料合併完成，總筆數: {len(df_all)}\n")

    if df_all.empty:
        print("錯誤：合併後無資料。")
    else:
        # 跑所有組合的迴歸
        all_results = {}
        summary_rows = []

        for group_name, hours in GROUPS.items():
            print(f"=== {group_name} ===")
            for building in BUILDINGS:
                # 呼叫run_regression計算該建築該組的迴歸結果，並存到all_results字典裡，
                # key是(group_name, building)，value是迴歸結果的字典
                res = run_regression(df_all, building, group_name, hours)
                all_results[(group_name, building)] = res
                if res:
                    print(f"  {building}：斜率={res['斜率']}, "
                          f"R²={res['R²']}, p={res['p值']}, n={res['樣本數']}")
                    summary_rows.append({k: v for k, v in res.items() # 把回歸結果拆成一行，k是欄位名稱，v是值
                                         if not k.startswith('_')}) # 把_開頭的欄位排除掉，因為那些是繪圖用的，不需要放在摘要裡
            print()

        # 輸出摘要 CSV
        df_summary = pd.DataFrame(summary_rows)
        csv_out = os.path.join(BASE_OUTPUT_DIR, "regression_summary.csv")
        df_summary.to_csv(csv_out, index=False, encoding="utf-8-sig")
        print(f">> 摘要儲存：{csv_out}\n")
        print(df_summary.to_string(index=False))

        # 繪圖
        print("\n繪製圖表...")
        plot_scatter_comparison(all_results)
        plot_slope_bar(all_results)
        print("\n全部完成！")
