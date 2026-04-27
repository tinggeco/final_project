import pandas as pd
import os


def classroom_week(file_path, output_file):
    # 1. 讀取 CSV 檔案
    df = pd.read_csv(file_path)

    # 2. 設定節次欄位（第1節 ~ 第9節）
    period_cols = ['1', '2', '3', '4', '5', '6', '7', '8', '9']

    # 3. 判斷每個節次是否有課（只要包含 V 就算）
    for col in period_cols:
        df[col] = df[col].astype(str).str.contains("V", na=False)

    # 4. 計算每一列（每間教室）一天有幾節課
    df["當日課堂數"] = df[period_cols].sum(axis=1)

    # 5. 依照「學年度學期 + 星期」加總
    result = df.groupby(
        ["學年度學期", "星期"]
    )["當日課堂數"].sum().reset_index()

    # 6. 星期數字轉中文（1→星期一）
    weekday_map = {
        1: "星期一",
        2: "星期二",
        3: "星期三",
        4: "星期四",
        5: "星期五",
        6: "星期六",
        7: "星期日"
    }

    result["星期"] = result["星期"].map(weekday_map)

    # 7. 轉成橫向表格（Pivot Table）
    pivot_result = result.pivot(
        index="學年度學期",
        columns="星期",
        values="當日課堂數"
    )

    # 欄位順序固定（避免亂掉）
    ordered_cols = [
        "星期一", "星期二", "星期三",
        "星期四", "星期五", "星期六", "星期日"
    ]

    pivot_result = pivot_result.reindex(
        columns=[col for col in ordered_cols if col in pivot_result.columns]
    )

    # 8. 輸出成 CSV（只輸出橫向統計表）
    pivot_result.to_csv(
        output_file,
        encoding="utf-8-sig"
    )

    print(f"已成功輸出：{output_file}")


# =========================
# 主程式
# =========================

dir_path = r"D:\ntu\114-2環境科學\classroom_usage"

classrooms = os.listdir(dir_path)

for classroom in classrooms:
    if classroom.endswith("fast.csv"):
        file_path = os.path.join(dir_path, classroom)

        # 輸出檔名：例如 共館_fast.csv → 共館_week.csv
        output_file = os.path.join(
            dir_path,
            classroom.replace("fast.csv", "week.csv")
        )

        classroom_week(file_path, output_file)