import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

def setup_chinese_font():
    plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    print("中文字体配置完成，确保中文正常显示")


data_path = '../data/raw/油价预测_新增特征后的数据表.xlsx'
output_dir = '../outputs/'
target_var = 'Brent_Crude(BZ=F)_Close'

df = pd.read_excel(data_path)


exclude_cols = ['日期', target_var]
feature_cols = [col for col in df.columns if col not in exclude_cols and pd.api.types.is_numeric_dtype(df[col])]



correlation_results = []

for col in feature_cols:
    valid_data = df[[target_var, col]].dropna()

    from scipy.stats import pearsonr

    corr_coef, p_value = pearsonr(valid_data[target_var], valid_data[col])

    # 判断显著性和是否保留（|相关系数|>0.3）
    if p_value < 0.001:
        significance = '***'
    elif p_value < 0.01:
        significance = '**'
    elif p_value < 0.05:
        significance = '*'
    else:
        significance = '不显著'

    is_retained = '是' if abs(corr_coef) > 0.3 else '否'

    correlation_results.append({
        '特征名称': col,
        '相关系数': round(corr_coef, 4),
        '相关系数绝对值': round(abs(corr_coef), 4),
        'p值': round(p_value, 8),
        '显著性': significance,
        '是否保留（|r|>0.3）': is_retained
    })

corr_df = pd.DataFrame(correlation_results)
corr_df_sorted = corr_df.sort_values('相关系数绝对值', ascending=False).reset_index(drop=True)

retained_count = len(corr_df_sorted[corr_df_sorted['是否保留（|r|>0.3）'] == '是'])
total_count = len(corr_df_sorted)


retained_feature_names = corr_df_sorted[corr_df_sorted['是否保留（|r|>0.3）'] == '是']['特征名称'].tolist()
retained_data = df[['日期', target_var] + retained_feature_names].copy()

for i, feat in enumerate(retained_feature_names, 1):
    corr_val = corr_df_sorted[corr_df_sorted['特征名称'] == feat]['相关系数'].values[0]

excel_path = f'{output_dir}/油价特征相关性分析结果_最终版.xlsx'
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    corr_df_sorted.to_excel(writer, sheet_name='完整相关性结果', index=False)

    retained_data.to_excel(writer, sheet_name='保留的高相关特征数据', index=False)

    retained_corr_matrix = retained_data.drop('日期', axis=1).corr()
    retained_corr_matrix.to_excel(writer, sheet_name='保留特征相关性矩阵')



setup_chinese_font()

plt.figure(figsize=(14, 10))

retained_corr_data = corr_df_sorted[corr_df_sorted['是否保留（|r|>0.3）'] == '是'].copy()

retained_corr_data = retained_corr_data.sort_values('相关系数绝对值', ascending=True)

colors = ['#2E86AB' if x > 0 else '#A23B72' for x in retained_corr_data['相关系数']]

bars = plt.barh(retained_corr_data['特征名称'], retained_corr_data['相关系数'], color=colors, alpha=0.8,
                edgecolor='white', linewidth=0.5)

for bar, value in zip(bars, retained_corr_data['相关系数']):
    x_pos = value + 0.015 if value > 0 else value - 0.015
    plt.text(x_pos, bar.get_y() + bar.get_height() / 2,
             f'{value:.3f}', ha='left' if value > 0 else 'right',
             va='center', fontsize=10, fontweight='bold')

plt.axvline(x=0.3, color='#E74C3C', linestyle='--', linewidth=2, alpha=0.7, label='筛选阈值 |r|=0.3')
plt.axvline(x=-0.3, color='#E74C3C', linestyle='--', linewidth=2, alpha=0.7)
plt.axvline(x=0, color='#34495E', linestyle='-', linewidth=1.5, alpha=0.8)

plt.title(f'Brent原油收盘价与高相关特征的皮尔逊相关系数\n（共{len(retained_corr_data)}个特征，|r|>0.3）',
          fontsize=16, fontweight='bold', pad=20, color='#2C3E50')
plt.xlabel('皮尔逊相关系数', fontsize=12, fontweight='bold', color='#34495E')
plt.ylabel('特征名称', fontsize=12, fontweight='bold', color='#34495E')
plt.xlim(-0.6, 1.1)
plt.legend(loc='lower right', fontsize=11, frameon=True, shadow=True)
plt.grid(axis='x', alpha=0.3, linestyle='-', linewidth=0.5)
plt.tight_layout()

bar_chart_path = f'{output_dir}/高相关特征相关性条形图.png'
plt.savefig(bar_chart_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
plt.close()

plt.figure(figsize=(16, 14))

retained_vars = [target_var] + retained_feature_names
corr_matrix = retained_data[retained_vars].corr()

mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)  # k=1跳过对角线

cmap = plt.cm.RdBu_r
heatmap = plt.imshow(corr_matrix, cmap=cmap, vmin=-1, vmax=1)


for i in range(len(corr_matrix.columns)):
    for j in range(len(corr_matrix.columns)):
        if not mask[i, j]:
            text = plt.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                            ha="center", va="center", color="white" if abs(corr_matrix.iloc[i, j]) > 0.5 else "black",
                            fontsize=9, fontweight='bold')


plt.xticks(range(len(corr_matrix.columns)), corr_matrix.columns, rotation=45, ha='right', fontsize=10,
           fontweight='bold')
plt.yticks(range(len(corr_matrix.columns)), corr_matrix.columns, fontsize=10, fontweight='bold')

cbar = plt.colorbar(heatmap, shrink=0.8)
cbar.set_label('皮尔逊相关系数', fontsize=12, fontweight='bold', rotation=270, labelpad=20)
plt.title('保留特征与Brent原油收盘价的相关性热力图',
          fontsize=16, fontweight='bold', pad=20, color='#2C3E50')

plt.tight_layout()
heatmap_path = f'{output_dir}/保留特征相关性热力图.png'
plt.savefig(heatmap_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
plt.close()
print(f"📊 热力图已保存至：{heatmap_path}")

