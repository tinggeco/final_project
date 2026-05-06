# -*- coding: utf-8 -*-
"""
Created on Sun Apr 26 23:32:48 2026

@author: ting
"""

import pandas as pd
import os
import numpy as np

file_path = r"D:\ntu\114-2環境科學\classroom_usage\普通教學館_合併總表.xlsx"
output_file = r"D:\ntu\114-2環境科學\classroom_usage\output\普通_power_day.csv"


tables = pd.read_html(file_path)
df = tables[1].copy()

df = pd.read_csv(file_path)

# 把第 1 列設成欄位名稱
df.columns = df.iloc[0]
df.columns = (
    df.columns.astype(str)
    .str.replace("\xa0", " ", regex=False)
    .str.strip()
)
# 刪掉原本那一列標題資料
df = df.iloc[1:].reset_index(drop=True)
print(df.columns.tolist())


# =========================
# 2. 整理日期時間欄位
# =========================

df["日期時間"] = pd.to_datetime(df["日期時間"], errors="coerce")

# 移除日期時間無法轉換的資料
df = df.dropna(subset=["日期時間"]).copy()


# =========================
# 3. 新增星期欄位
# =========================

weekday_map = {
    0: "星期一",
    1: "星期二",
    2: "星期三",
    3: "星期四",
    4: "星期五",
    5: "星期六",
    6: "星期日"
}

df["星期"] = df["日期時間"].dt.weekday.map(weekday_map)


# =========================
# 4. 新增小時欄位
# =========================
# 例如：
# 08:00 → 8
# 09:00 → 9

df["小時"] = df["日期時間"].dt.hour


# 如果你想顯示成 08:00~09:00，可另外產生這個欄位
df["時間區間"] = (
    df["小時"].astype(str).str.zfill(2)
    + ":00~"
    + (df["小時"] + 1).astype(str).str.zfill(2)
    + ":00"
)


# =========================
# 5. 判斷年度學期
# =========================

def assign_semester(dt):
    if pd.Timestamp("2024-09-02") <= dt <= pd.Timestamp("2024-12-13 23:59:59"):
        return "113-1"
    elif pd.Timestamp("2025-02-17") <= dt <= pd.Timestamp("2025-05-29 23:59:59"):
        return "113-2"
    elif pd.Timestamp("2025-09-01") <= dt <= pd.Timestamp("2025-12-12 23:59:59"):
        return "114-1"
    elif pd.Timestamp("2026-02-23") <= dt <= pd.Timestamp("2026-06-05 23:59:59"):
        return "114-2"
    else:
        return np.nan


df["年度學期"] = df["日期時間"].apply(assign_semester)

# 只保留有落在學期區間內的資料
df = df.dropna(subset=["年度學期"]).copy()


# =========================
# 6. 整理功率欄位
# =========================

power_col = "功率 kW"

df[power_col] = pd.to_numeric(df[power_col], errors="coerce")

# 移除功率無法轉成數字的資料
df = df.dropna(subset=[power_col]).copy()


# =========================
# 7. 定義：剔除 2 倍標準差後取平均
# =========================

def mean_without_2std(group):
    mean = group[power_col].mean()
    std = group[power_col].std()

    # 如果該組只有一筆資料，std 會是 NaN，直接回傳平均
    if pd.isna(std) or std == 0:
        return mean

    lower = mean - 2 * std
    upper = mean + 2 * std

    filtered = group[
        (group[power_col] >= lower) &
        (group[power_col] <= upper)
    ]

    return filtered[power_col].mean()


# =========================
# 8. groupby 統計
# =========================

result = (
    df.groupby(["年度學期", "星期", "小時", "時間區間"])
      .apply(mean_without_2std)
      .reset_index(name="平均功率_kW")
)


# =========================
# 9. 排序
# =========================

semester_order = ["113-1", "113-2", "114-1", "114-2"]
weekday_order = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

result["年度學期"] = pd.Categorical(
    result["年度學期"],
    categories=semester_order,
    ordered=True
)

result["星期"] = pd.Categorical(
    result["星期"],
    categories=weekday_order,
    ordered=True
)

result = result.sort_values(["年度學期", "星期", "小時"])


# =========================
# 10. 輸出 CSV
# =========================

result.to_csv(output_file, index=False, encoding="utf-8-sig")

print(result)
print(f"已成功輸出：{output_file}")