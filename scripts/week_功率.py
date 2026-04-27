# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 12:03:30 2026

@author: ting
"""

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

        # 如果不想要負值，可以取消註解
        # result["扣除基礎後功率_kW"] = result["扣除基礎後功率_kW"].clip(lower=0)

        # =========================
        # 8. 只保留 08:00~17:00
        # =========================
        # 小時 = 8 代表 08:00~09:00
        # 小時 = 16 代表 16:00~17:00
        # 所以保留 8 <= 小時 < 17

        result = result[
            (result["小時"] >= 8) &
            (result["小時"] < 17)
        ].copy()

        # =========================
        # 9. groupby：年度學期、星期 加總
        # =========================

        summary = (
            result
            .groupby(["年度學期", "星期"], as_index=False)["扣除基礎後功率_kW"]
            .sum()
        )

        summary = summary.rename(columns={
            "扣除基礎後功率_kW": "功率_kW"
        })

        # =========================
        # 10. 排序
        # =========================

        summary["星期"] = pd.Categorical(
            summary["星期"],
            categories=weekday_order,
            ordered=True
        )

        summary = summary.sort_values(["年度學期", "星期"])

        # =========================
        # 11. 輸出 CSV
        # =========================

        building_name = file.replace("_每小時平均功率.csv", "")

        output_file = os.path.join(
            dir_path,
            f"{building_name}_power_week.csv"
        )

        summary.to_csv(output_file, index=False, encoding="utf-8-sig")

        print(f"已輸出：{output_file}")
        print(summary)