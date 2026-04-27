# -*- coding: utf-8 -*-

import pandas as pd
import os

def class_period(file_path, output_file):
    df = pd.read_csv(file_path)
    
    # 第1節～第9節
    period_cols = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
    
    # 判斷每一節是否有課，有 V 就算 1，沒有就算 0
    for col in period_cols:
        df[col] = df[col].astype(str).str.contains("V", na=False).astype(int)
    
    # 依照「學年度學期 + 星期」統計每一節有幾堂課
    result = df.groupby(
        ["學年度學期", "星期"]
    )[period_cols].sum().reset_index()
    
    # 星期數字轉中文
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
    
    # 只保留星期一～星期五
    result = result[result["星期"].isin(["星期一", "星期二", "星期三", "星期四", "星期五"])]
    
    # 欄位名稱改成比較清楚
    rename_map = {
    '1': '08:00~09:00',
    '2': '09:00~10:00',
    '3': '10:00~11:00',
    '4': '11:00~12:00',
    '5': '12:00~13:00',
    '6': '13:00~14:00',
    '7': '14:00~15:00',
    '8': '15:00~16:00',
    '9': '16:00~17:00'
    }
    
    result = result.rename(columns=rename_map)
    
    # 輸出 CSV
    result.to_csv(output_file, index=False, encoding="utf-8-sig")
    
    print(result)
    print(f"已成功輸出：{output_file}")
    

# =========================
# 主程式
# =========================

dir_path = r"D:\ntu\114-2環境科學\classroom_usage"
output_path = r'D:\ntu\114-2環境科學\classroom_usage\data'

classrooms = os.listdir(dir_path)

for classroom in classrooms:
    if classroom.endswith("fast.csv"):
        file_path = os.path.join(dir_path, classroom)

        # 輸出檔名：例如 共館_fast.csv → 共館_week.csv
        output_file = os.path.join(
            output_path,
            classroom.replace("fast.csv", "day.csv")
        )

        class_period(file_path, output_file)