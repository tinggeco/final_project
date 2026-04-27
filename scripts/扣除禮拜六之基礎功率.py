# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 11:56:27 2026

@author: ting
"""

import pandas as pd
import os


# =========================
# 1. 設定資料夾
# =========================

dir_path = r"D:\ntu\114-2環境科學\classroom_usage\data"

output_dir = os.path.join(dir_path, "baseline_removed")
os.makedirs(output_dir, exist_ok=True)


# =========================
# 2. 設定要處理的星期
# =========================

weekday_order = ["星期一", "星期二", "星期三", "星期四", "星期五"]
baseline_weekday = "星期六"


# =========================
# 3. 逐一處理每個「每小時平均功率」檔案
# =========================

for file in os.listdir(dir_path):

    if file.endswith("每小時平均功率.csv"):

        file_path = os.path.join(dir_path, file)

        print(f"正在處理：{file}")

        df = pd.read_csv(file_path, encoding="utf-8-sig")

        # 清理欄位名稱
        df.columns = (
            df.columns.astype(str)
            .str.replace("\xa0", " ", regex=False)
            .str.strip()
        )

        # 確保欄位型態正確
        df["小時"] = pd.to_numeric(df["小時"], errors="coerce")
        df["平均功率_kW"] = pd.to_numeric(df["平均功率_kW"], errors="coerce")

        df = df.dropna(subset=["年度學期", "星期", "小時", "平均功率_kW"]).copy()

        # =========================
        # 4. 取出星期六作為 baseline
        # =========================

        baseline = df[df["星期"] == baseline_weekday].copy()

        baseline = baseline[["年度學期", "小時", "平均功率_kW"]]

        baseline = baseline.rename(columns={
            "平均功率_kW": "星期六基礎功率_kW"
        })

        # =========================
        # 5. 取出星期一～五
        # =========================

        weekday_df = df[df["星期"].isin(weekday_order)].copy()

        # =========================
        # 6. 依照「年度學期 + 小時」合併星期六 baseline
        # =========================

        result = weekday_df.merge(
            baseline,
            on=["年度學期", "小時"],
            how="left"
        )

        # =========================
        # 7. 扣掉星期六基礎功率
        # =========================

        result["扣除基礎後功率_kW"] = (
            result["平均功率_kW"] - result["星期六基礎功率_kW"]
        )

        # 如果你不希望出現負值，可以打開這行
        # result["扣除基礎後功率_kW"] = result["扣除基礎後功率_kW"].clip(lower=0)

        # =========================
        # 8. 只保留 07:00~18:00
        # =========================
        # 小時 = 7 代表 07:00~08:00
        # 小時 = 17 代表 17:00~18:00
        # 所以保留 7 <= 小時 < 18

        result = result[
            (result["小時"] >= 7) &
            (result["小時"] < 18)
        ].copy()

        # =========================
        # 9. 排序
        # =========================

        result["星期"] = pd.Categorical(
            result["星期"],
            categories=weekday_order,
            ordered=True
        )

        result = result.sort_values(["年度學期", "星期", "小時"])

        # =========================
        # 10. 輸出 CSV
        # =========================

        building_name = file.replace("_每小時平均功率.csv", "")

        output_file = os.path.join(
            output_dir,
            f"{building_name}_扣除星期六基礎功率_0700_1800.csv"
        )

        result.to_csv(output_file, index=False, encoding="utf-8-sig")

        print(f"已輸出：{output_file}")