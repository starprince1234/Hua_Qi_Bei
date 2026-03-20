import pandas as pd

# ============ 1. 读取原始文件 ============
file_path = '../data/processed/油价预测7日波动率因子表.xlsx'
df = pd.read_excel(file_path)

print("=== 修复前 ===")
print(f"总行数：{len(df)}")
print(f"衰减系数空值数量：{df['衰减系数'].isna().sum()}")
print(f"衰减系数空值比例：{df['衰减系数'].isna().mean():.2%}")

# ============ 2. 填充空值为 0 ============
df['衰减系数'] = df['衰减系数'].fillna(0)

# ============ 3. 确保是数值类型 ============
df['衰减系数'] = pd.to_numeric(df['衰减系数'], errors='coerce').fillna(0)

# ============ 4. 验证修复结果 ============
print("\n=== 修复后 ===")
print(f"衰减系数空值数量：{df['衰减系数'].isna().sum()}")
print(f"衰减系数数据类型：{df['衰减系数'].dtype}")
print(f"衰减系数非空值数量：{df['衰减系数'].notna().sum()}")

# ============ 5. 保存新文件 ============
output_path = '../data/processed/油价预测 7 日波动率因子表_fixed.xlsx'
df.to_excel(output_path, index=False)

print(f"\n✓ 修复完成！文件已保存至：{output_path}")
