# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 12:08:01 2026

@author: ting
"""

# -*- coding: utf-8 -*-

import pandas as pd
import os


# =========================
# 1. 設定檔案路徑
# =========================

dir_path = r"D:\ntu\114-2環境科學\classroom_usage\data"

power_file = os.path.join(
    dir_path,
    "baseline_removed",
    "新生_week.csv"
)

class_file = r"D:\ntu\114-2環境科學\classroom_usage\data\新生_classroom_usage_week.csv"

output_file = os.path.join(
    dir_path,
    "新生_功率除以課堂數.csv"
)


# =========================
# 2. 讀取資料
# =========================

power_df = pd.read_csv(power_file, encoding="utf-8-sig")
class_df = pd.read_csv(class_file, encoding="utf-8-sig")


# =========================
# 3. 清理欄位名稱
# =========================

power_df.columns = power_df.columns.astype(str).str.strip()
class_df.columns = class_df.columns.astype(str).str.strip()


# =========================
# 4. 統一功率欄位名稱
# =========================
# 你的檔案可能叫：
# 功率_kW
# 或 0800_1700扣除基礎後功率總和_kW

if "0800_1700扣除基礎後功率總和_kW" in power_df.columns:
    power_df = power_df.rename(columns={
        "0800_1700扣除基礎後功率總和_kW": "功率_kW"
    })


# =========================
# 5. 將課堂數資料從寬表轉長表
# =========================
# 原本：
# 學年度學期 | 星期一 | 星期二 | 星期三 ...
#
# 轉成：
# 年度學期 | 星期 | 課堂數

class_long = class_df.melt(
    id_vars="學年度學期",
    var_name="星期",
    value_name="課堂數"
)


# =========================
# 6. 學年度學期格式轉換
# =========================
# 1131 → 113-1
# 1132 → 113-2
# 1141 → 114-1

class_long["學年度學期"] = class_long["學年度學期"].astype(str)

class_long["年度學期"] = (
    class_long["學年度學期"].str[:3]
    + "-"
    + class_long["學年度學期"].str[3]
)

class_long = class_long.drop(columns=["學年度學期"])


# =========================
# 7. 課堂數轉成數字
# =========================

class_long["課堂數"] = pd.to_numeric(class_long["課堂數"], errors="coerce")


# =========================
# 8. 合併功率資料與課堂數資料
# =========================

merged = power_df.merge(
    class_long,
    on=["年度學期", "星期"],
    how="left"
)


# =========================
# 9. 計算 功率 / 課堂數
# =========================

merged["功率_每堂課_kW"] = merged["功率_kW"] / merged["課堂數"]

# 避免課堂數為 0 時出現 inf
merged.loc[merged["課堂數"] == 0, "功率_每堂課_kW"] = pd.NA


# =========================
# 10. 排序
# =========================

semester_order = ["113-1", "113-2", "114-1", "114-2"]
weekday_order = ["星期一", "星期二", "星期三", "星期四", "星期五"]

merged["年度學期"] = pd.Categorical(
    merged["年度學期"],
    categories=semester_order,
    ordered=True
)

merged["星期"] = pd.Categorical(
    merged["星期"],
    categories=weekday_order,
    ordered=True
)

merged = merged.sort_values(["年度學期", "星期"])


# =========================
# 11. 輸出 CSV
# =========================

merged.to_csv(output_file, index=False, encoding="utf-8-sig")

print(merged)
print(f"已成功輸出：{output_file}")