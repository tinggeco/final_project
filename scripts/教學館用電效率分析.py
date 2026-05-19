# -*- coding: utf-8 -*-
"""
分析不同時段，每堂課的平均功耗（kW/堂），比較不同教學館在不同時段的用電效率差異。
圖表說明：
- 箱型圖：平均每堂課功耗（左軸）
- 紅線：原始功耗平均值（右軸1）
- 藍線：課堂數平均值（右軸2）
"""

import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns

# 基本資料設定
BUILDINGS = ["新生", "博雅", "共同", "普通"]
BASE_OUTPUT_DIR = "output"
FIGURE_OUTPUT_DIR = os.path.join(BASE_OUTPUT_DIR, "figures_comparison")

PALETTE = {
    "新生": "#8172B2",
    "博雅": "#55A868",
    "共同": "#4C72B0",
    "普通": "#C44E52"
}
HOURS = [8, 9, 10, 11, 12, 13, 14, 15, 16]

os.makedirs(FIGURE_OUTPUT_DIR, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei"] # 中文字體設微軟正黑體
plt.rcParams["axes.unicode_minus"] = False # 負號正常顯示


# 資料載入
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

# 處理課堂數資料，由寬轉長，並將欄位名稱與power統一，方便後續合併分析
def melt_classroom_data(df_cls):
    sem_col  = '學年度學期'
    day_col  = '星期'
    time_cols = [c for c in df_cls.columns if '~' in str(c)] # 因為原始資料是8:00~9:00這種格式的欄位名稱
    if not all([sem_col, day_col, time_cols]):
        raise ValueError("課堂數資料缺少必要欄位")

    # 將資料由寬轉長，並統一欄位名稱
    df_long = df_cls.melt(
        id_vars=[sem_col, day_col], value_vars=time_cols, # 把拆下來的時間區間欄位命名為"時間區間"，課堂數命名為"課堂數"
        var_name='時間區間', value_name='課堂數'
    ).rename(columns={sem_col: '年度學期'}) # 統一欄位名稱，把學年度學期改成年度學期

    # 針對年度學期stripe去除空白字元，並統一格式（例如：1142 → 114-2），目的是跟後面power格式相同
    df_long['年度學期'] = df_long['年度學期'].astype(str).str.strip().apply( #.apply()套用到每一個值
        # 如果是4位數且中間沒有'-'，就插入'-'，例如1142 → 114-2；否則保持原樣
        # [:3]取前3個字元，[3]取第4個字元
        lambda x: f'{x[:3]}-{x[3]}' if len(x) == 4 and '-' not in x else x 
    )
    df_long['星期'] = df_long['星期'].astype(str).str.strip() # strip處理一下
    df_long['時間區間'] = df_long['時間區間'].astype(str).str.strip() # strip處理一下
    df_long['課堂數'] = pd.to_numeric(df_long['課堂數'], errors='coerce') # 轉換為數值型態(numeric)，無法轉換的設為NaN
    return df_long

# 將單一建築的功率資料與課堂數資料合併，回傳合併後的DataFrame
def get_merged_data_for_building(building):
    print(f"-- 正在處理: {building}")
    df_power = load_data(building, "power") # 呼叫load_data載入功率資料
    df_class = load_data(building, "class") # 呼叫load_data載入課堂數資料
    if df_power is None or df_class is None:
        return None

    # 欄位名稱基本清洗，呼叫melt_classroom_data讓課堂數資料與power資料格式統一
    df_power.columns = df_power.columns.str.strip()
    df_class.columns = df_class.columns.str.strip()
    df_class_long = melt_classroom_data(df_class) # 呼叫melt_classroom_data處理課堂數資料

    # 對欄位內容stripe，確保合併前的欄位格式一致
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
    return merged


# 繪圖
def draw_subplot(ax, building, df_all, df_plot, box_yrange=None):
    
    box_color = PALETTE.get(building) # 取前面定義的建物顏色
    # 創立一個包含所有小時的DataFrame，確保後續繪圖不會因為某些小時缺資料而斷線或缺點
    base = pd.DataFrame({'小時': HOURS}) # HOURS前面定義好了，8~16點

    # 統計量
    hourly = (
        df_all[df_all['建築'] == building].groupby('小時').agg( # 用.agg()聚合
            avg_power=('扣除基礎後功率_kW', 'mean'), # 計算每小時的平均功率
            avg_classes=('課堂數', 'mean')) # 計算每小時的平均課堂數
        .reset_index() # 把小時索引拿掉
    )
    # on='小時'以小時為基準合併，how='left'確保所有小時都保留(對照base)，缺的部分會是NaN
    hourly = base.merge(hourly, on='小時', how='left')   

    bdata = df_plot[df_plot['建築'] == building] # 把單棟建築的資料過濾出來，準備繪箱型圖用

    # 箱型圖
    if bdata.empty:
        ax.text(0.5, 0.5, '無資料', ha='center', va='center', fontsize=12)
        ax.set_title(f'{building}館', fontsize=14)
        return

    sns.boxplot(
        x='小時', y='power_per_class', data=bdata, order=HOURS, ax=ax,
        color=box_color,
        boxprops=dict(alpha=.75), # 稍微透明，才可以看到格線
        medianprops=dict(linewidth=2, color='white') # 設定中位數線的樣式，讓它更明顯一些
    )
    ax.set_title(f'{building}館', fontsize=14, fontweight='bold')
    ax.set_ylabel('平均每堂課功耗 (kW/堂)', color=box_color, fontsize=10)
    ax.tick_params(axis='y', labelcolor=box_color, labelsize=9)
    ax.set_xlabel('')
    ax.grid(True, axis='y', linestyle='--', alpha=0.4)

    if box_yrange is not None:
        ax.set_ylim(box_yrange)

    # 因為Seaborn的箱型圖會把x軸的類別轉成0,1,2...這些位置，
    # 所以我們要自己定義x軸的位置，對應到HOURS的順序，這樣才能讓後面兩條折線圖對齊正確的位置
    x_pos = list(range(len(HOURS)))

    # 右軸1：原始功耗均值（紅）
    # 這裡用twinx()創建共用x軸的第二個y軸，然後在這個軸上繪製原始功耗均值的折線圖
    ax_power = ax.twinx()
    ax_power.plot(
        x_pos, hourly['avg_power'],
        color='#d62728', marker='o', linestyle='--',
        linewidth=1.8, markersize=5, label='原始功耗均值 (kW)'
    )
    ax_power.set_ylabel('原始功耗均值 (kW)', color='#d62728', fontsize=10)
    ax_power.tick_params(axis='y', labelcolor='#d62728', labelsize=9)
    ax_power.grid(False)

    # 右軸2：課堂數均值（藍）
    # 將第三軸往右偏移，避免與ax_power重疊
    ax_cls = ax.twinx()
    ax_cls.spines['right'].set_position(('axes', 1.18))   # 偏移一點，讓它在右側外緣
    ax_cls.plot(
        x_pos, hourly['avg_classes'],
        color='#1f77b4', marker='X', linestyle=':',
        linewidth=1.8, markersize=6, label='課堂數均值 (堂)'
    )
    ax_cls.set_ylabel('課堂數均值 (堂)', color='#1f77b4', fontsize=10)
    ax_cls.tick_params(axis='y', labelcolor='#1f77b4', labelsize=9)
    ax_cls.grid(False)

    return ax_power, ax_cls



#主繪圖函式
def make_figure(df_all, df_plot, fixed_ylim, filename):
    """
    fixed_ylim : (ymin, ymax) 或 None
    """
    # 建立2x2子圖，figsize調整整體大小，suptitle設定總標題，fig.text添加說明文字
    fig, axes = plt.subplots(2, 2, figsize=(20, 13))
    fig.suptitle(f'各教學館用電效率分析圖',
                 fontsize=18, fontweight='bold', y=0.98)
    fig.text(0.5, 0.945,
             '箱形圖: 平均每堂課功耗（左軸）｜紅線: 原始功耗平均值（右軸1）｜藍線: 課堂數平均值（右軸2）',
             fontsize=11, ha='center')

    # 先把axes flat成左上到右下的順序，然後用zip配對建築名稱和子圖，再呼叫draw_subplot繪製每個子圖
    for ax, building in zip(axes.flat, BUILDINGS):
        draw_subplot(ax, building, df_all, df_plot, box_yrange=fixed_ylim) # 呼叫draw_subplot繪製子圖，傳入固定的Y軸範圍

    # 共用X軸標籤，放在整體圖的下方中央
    fig.text(0.5, 0.02, '小時（整點）', ha='center', fontsize=13)

    # 統一圖例，因為每個子圖的右軸都有兩條線，
    # 所以我們只需要取其中一個子圖的右軸來創建圖例就好，這裡選第一個子圖的ax_power和ax_cls
    from matplotlib.lines import Line2D # 用Line2D手動創建圖例元素，因為matplotlib沒辦法自動把三個軸的圖例合併成一個
    legend_elements = [
        # [0], [0] 就是隨便給的座標，反正不會顯示出來，只是Line2D需要有座標才能建立物件。
        Line2D([0], [0], color='#d62728', marker='o', linestyle='--',
               linewidth=1.8, markersize=5, label='原始功耗均值 (kW)'),
        Line2D([0], [0], color='#1f77b4', marker='X', linestyle=':',
               linewidth=1.8, markersize=6, label='課堂數均值 (堂)'),
    ]
    fig.legend(handles=legend_elements, loc='upper right',
               bbox_to_anchor=(0.98, 0.96), fontsize=11) # 放右上角

    # 用tight_layout調整子圖間距，rect參數留出空間給suptitle和說明文字，最後儲存圖檔
    plt.tight_layout(rect=[0.03, 0.04, 0.96, 0.93])
    out = os.path.join(FIGURE_OUTPUT_DIR, filename)
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f">> 圖表儲存：{out}")


# 主程式
if __name__ == "__main__":

    # 呼叫get_merged_data_for_building處理每個建築的資料，回傳合併後的DataFrame
    dfs = [get_merged_data_for_building(b) for b in BUILDINGS] 

    # 用pd.concat垂直疊加所有建築的DataFrame，ignore_index=True重置索引
    df_all = pd.concat([d for d in dfs if d is not None], ignore_index=True)

    # 先split分割時間區間，取開始時間的部分，再split":"取小時，最後轉換為整數
    df_all['小時'] = (df_all['時間區間'].str.split('~').str[0].str.split(':').str[0].astype(int))

    # assign df_all為欄位'小時'，位於HOURS區間的資料
    df_all = df_all[df_all['小時'].isin(HOURS)].copy()
    print(f"資料合併完成，總筆數: {len(df_all)}")

    if df_all.empty:
        print("錯誤：合併後無資料。")
    else:
        # 先把NA值過濾掉
        df_analysis = df_all.dropna(subset=['扣除基礎後功率_kW', '課堂數'])
        # 再過濾掉課堂數為0的資料，避免除以0出現無限大
        df_analysis = df_analysis[df_analysis['課堂數'] > 0].copy()
        # 計算每堂課的平均功率（kW/堂）
        df_analysis['power_per_class'] = (
            df_analysis['扣除基礎後功率_kW'] / df_analysis['課堂數']
        )

        # 為避免極端值影響繪圖，對每個館過濾power_per_class PR99以上的資料點
        df_plot_list = []
        for b in BUILDINGS:
            sub = df_analysis[df_analysis['建築'] == b].copy()
            if sub.empty:
                continue
            p99 = sub['power_per_class'].quantile(0.99)
            # 一個帥氣的寫法，先把小於PR99的資料點設為TRUE，然後用這個布林值選擇要append進入df_plot_list的資料
            df_plot_list.append(sub[sub['power_per_class'] <= p99])
        # 一樣用.concat()把過濾後的資料垂直疊加成一個DataFrame，ignore_index=True重置索引
        df_plot = pd.concat(df_plot_list, ignore_index=True)
        print(f"過濾極端值後，用於分析的資料筆數: {len(df_plot)}")

        # 開始畫圖，Y軸範圍固定，四棟建物才可以比較
        # 取所有館過濾後 power_per_class 的全域 1%~99% 作為統一範圍
        global_min = df_plot['power_per_class'].quantile(0.01)
        global_max = df_plot['power_per_class'].quantile(0.99)
        # 稍微padding，不然資料點會疊到邊界
        pad = (global_max - global_min) * 0.05
        unified_ylim = (global_min - pad, global_max + pad)
        print(f"\n統一 Y 軸範圍: {unified_ylim[0]:.2f} ~ {unified_ylim[1]:.2f} kW/堂")

        print("繪製中...")
        make_figure(
            df_all, df_plot,
            fixed_ylim=unified_ylim,
            filename="各棟建築不同時段平均課堂耗電功率.png"
        )

        print("\n全部完成！")