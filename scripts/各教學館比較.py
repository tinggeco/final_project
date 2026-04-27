# -*- coding: utf-8 -*-

import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns


# =========================
# 1. 設定資料夾
# =========================

dir_path = r"D:\ntu\114-2環境科學\classroom_usage\data"

output_dir = os.path.join(dir_path, "figures")
os.makedirs(output_dir, exist_ok=True)


# =========================
# 2. 設定中文字型與 seaborn 風格
# =========================

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei"]
plt.rcParams["axes.unicode_minus"] = False

sns.set_theme(style="whitegrid", font="Microsoft JhengHei")


# =========================
# 3. 設定比較基準
# =========================

target_semester = "114-1"
target_weekday = "星期一"


# =========================
# 4. 讀取所有教學館資料
# =========================

all_plot_data = []

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

        # 確保資料型態正確
        df["小時"] = pd.to_numeric(df["小時"], errors="coerce")
        df["平均功率_kW"] = pd.to_numeric(df["平均功率_kW"], errors="coerce")

        # 篩選指定學期 + 星期
        temp = df[
            (df["年度學期"].astype(str) == target_semester) &
            (df["星期"].astype(str) == target_weekday)
        ].copy()

        temp = temp.dropna(subset=["小時", "平均功率_kW"])

        if temp.empty:
            print(f"{file} 沒有 {target_semester} {target_weekday} 的資料，跳過")
            continue

        # 從檔名取教學館名稱
        building_name = file.replace("_每小時平均功率.csv", "")

        temp["教學館"] = building_name

        all_plot_data.append(temp)


# =========================
# 5. 合併成 seaborn 可用格式
# =========================

if len(all_plot_data) == 0:
    raise ValueError(f"沒有找到 {target_semester} {target_weekday} 的資料")

plot_df = pd.concat(all_plot_data, ignore_index=True)

plot_df = plot_df.sort_values(["教學館", "小時"])


# =========================
# 6. 用 seaborn 畫圖
# =========================

plt.figure(figsize=(12, 6))

sns.lineplot(
    data=plot_df,
    x="小時",
    y="平均功率_kW",
    hue="教學館",
    marker="o",
    linewidth=2
)


# =========================
# 7. 圖表設定
# =========================

plt.title(
    f"{target_semester} {target_weekday} 各教學館每小時平均功率比較",
    fontsize=16,
    fontweight="bold"
)

plt.xlabel("時間", fontsize=12)
plt.ylabel("平均功率 kW", fontsize=12)

plt.xticks(
    ticks=range(0, 24),
    labels=[f"{h:02d}:00" for h in range(0, 24)],
    rotation=45
)

plt.legend(title="教學館", bbox_to_anchor=(1.02, 1), loc="upper left")
plt.tight_layout()


# =========================
# 8. 輸出圖片
# =========================

output_fig = os.path.join(
    output_dir,
    f"{target_semester}_{target_weekday}_各教學館每小時平均功率比較_seaborn.png"
)

plt.savefig(output_fig, dpi=300, bbox_inches="tight")
plt.show()

print(f"已輸出圖片：{output_fig}")