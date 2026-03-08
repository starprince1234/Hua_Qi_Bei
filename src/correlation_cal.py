import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
import os

warnings.filterwarnings('ignore')

# 设置中文字体和绘图样式
plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']
plt.rcParams['axes.unicode_minus'] = False
plt.style.use('default')

output_dir = '../outputs/'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
else:

df = pd.read_excel('../data/raw/油价预测_新增特征后的数据表（涨跌幅汇总）.xlsx')

# 定义5个标准格式目标变量
target_variables = [
    'Brent_close_1日涨跌幅(%)',
    'Brent_close_3日涨跌幅(%)',
    'Brent_close_7日涨跌幅(%)',
    'Brent_close_14日涨跌幅(%)',
    'Brent_close_30日涨跌幅(%)'
]

missing_targets = [var for var in target_variables if var not in df.columns]
if missing_targets:
    raise ValueError(f"数据中缺少目标变量：{missing_targets}\n请检查列名格式是否为Brent_close_XX日涨跌幅(%)")
else:
    for i, var in enumerate(target_variables, 1):
        print(f"   {i}. {var}")


def clean_dataset(df, target_vars):
    cleaned_df = df.copy()

    target_clean_info = []
    for target in target_vars:
        try:
            if cleaned_df[target].dtype == 'object':
                cleaned_df[target] = cleaned_df[target].astype(str).str.replace(' ', '', regex=False)
                cleaned_df[target] = pd.to_numeric(cleaned_df[target], errors='coerce')
            else:
                cleaned_df[target] = cleaned_df[target].astype(float)

            valid_count = cleaned_df[target].notna().sum()
            target_clean_info.append({
                '目标变量名称': target,  # 修复KeyError：使用明确的列名
                '有效数据量': f"{valid_count}/{len(cleaned_df)}",
                '均值(%)': round(cleaned_df[target].mean(), 4),
                '最大值(%)': round(cleaned_df[target].max(), 4),
                '最小值(%)': round(cleaned_df[target].min(), 4)
            })
        except Exception as e:
            raise ValueError(f"目标变量{target}清理失败：{str(e)}")

    feature_cols = [col for col in cleaned_df.columns if col not in ['日期'] + target_vars]
    non_numeric_features = []

    for col in feature_cols:
        try:
            if cleaned_df[col].dtype == 'object':
                cleaned_df[col] = cleaned_df[col].astype(str).str.replace(' ', '', regex=False)
                cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')
            else:
                cleaned_df[col] = cleaned_df[col].astype(float)
        except Exception as e:
            non_numeric_features.append(f"{col}: {str(e)[:50]}")
            cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')

    valid_feature_cols = []
    for col in feature_cols:
        valid_count = 0
        for target in target_vars:
            valid = cleaned_df[[target, col]].dropna().shape[0]
            valid_count += valid
        if valid_count >= 50:  # 总有效样本≥50，确保对多数目标变量有效
            valid_feature_cols.append(col)
        else:

    target_info_df = pd.DataFrame(target_clean_info)

    return cleaned_df, valid_feature_cols, target_info_df


df_clean, valid_feature_cols, target_info_df = clean_dataset(df, target_variables)


def analyze_target(target_name, df, feature_cols, output_dir):

    corr_results = []
    for feat in feature_cols:
        valid_data = df[[target_name, feat]].dropna()
        valid_count = len(valid_data)

        if valid_count < 20:
            corr = np.nan
            corr_strength = '样本不足'
        else:
            corr = valid_data[target_name].corr(valid_data[feat])
            if abs(corr) >= 0.3:
                corr_strength = '高相关'
            elif abs(corr) >= 0.1:
                corr_strength = '中等相关'
            else:
                corr_strength = '低相关'

        corr_results.append({
            '特征名称': feat,
            f'与{target_name}的相关系数': round(corr, 4) if pd.notna(corr) else 'NaN',
            '相关系数绝对值': round(abs(corr), 4) if pd.notna(corr) else 'NaN',
            '有效样本数': valid_count,
            '相关性强度': corr_strength
        })

    corr_df = pd.DataFrame(corr_results)
    strength_order = {'高相关': 0, '中等相关': 1, '低相关': 2, '样本不足': 3}
    corr_df['强度排序'] = corr_df['相关性强度'].map(strength_order)
    corr_df = corr_df.sort_values(['强度排序', '相关系数绝对值'], ascending=[True, False])
    corr_df = corr_df.drop('强度排序', axis=1).reset_index(drop=True)

    # Excel文件名（含目标变量名称，避免冲突）
    excel_filename = f"{output_dir}{target_name}_相关性分析结果.xlsx"
    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
        corr_df.to_excel(writer, sheet_name='完整结果', index=False)
        corr_df[corr_df['相关性强度'] == '高相关'].to_excel(writer, sheet_name='高相关(|r|≥0.3)', index=False)
        corr_df[corr_df['相关性强度'] == '中等相关'].to_excel(writer, sheet_name='中等相关(0.1≤|r|<0.3)', index=False)
        corr_df[corr_df['相关性强度'] == '低相关'].to_excel(writer, sheet_name='低相关(|r|<0.1)', index=False)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    fig.suptitle(f'目标变量：{target_name}', fontsize=14, fontweight='bold')

    valid_corr = corr_df[corr_df['相关性强度'] != '样本不足'].head(15)
    if len(valid_corr) > 0:
        colors = ['#e74c3c' if x > 0 else '#3498db' for x in valid_corr[f'与{target_name}的相关系数'].replace('NaN', 0)]
        y_pos = range(len(valid_corr))
        bars = ax1.barh(y_pos, valid_corr[f'与{target_name}的相关系数'].replace('NaN', 0), color=colors, alpha=0.8)

        y_labels = [name[:20] + '...' if len(name) > 20 else name for name in valid_corr['特征名称']]
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(y_labels, fontsize=9)
        ax1.set_xlabel('Pearson相关系数', fontsize=11)
        ax1.set_title('Top15相关特征', fontsize=12, fontweight='bold')
        ax1.axvline(x=0.3, color='#e74c3c', linestyle='--', alpha=0.7, label='高相关阈值')
        ax1.axvline(x=-0.3, color='#3498db', linestyle='--', alpha=0.7)
        ax1.legend(fontsize=9)

        for i, bar in enumerate(bars):
            width = bar.get_width()
            if width != 0:
                ax1.text(width + 0.005 if width > 0 else width - 0.005,
                         bar.get_y() + bar.get_height() / 2,
                         f'{width:.3f}', ha='left' if width > 0 else 'right',
                         va='center', fontsize=8)

    high_corr_feats = valid_corr[valid_corr['相关性强度'] == '高相关']['特征名称'].tolist()
    if len(high_corr_feats) >= 3:
        heatmap_vars = high_corr_feats + [target_name]
        heatmap_data = df[heatmap_vars].dropna()
        if len(heatmap_data) >= 30:
            heatmap_corr = heatmap_data.corr().round(3)
            im = ax2.imshow(heatmap_corr.values, cmap='RdBu_r', vmin=-1, vmax=1)

            heatmap_labels = [name[:15] + '...' if len(name) > 15 else name for name in heatmap_vars]
            ax2.set_xticks(range(len(heatmap_vars)))
            ax2.set_yticks(range(len(heatmap_vars)))
            ax2.set_xticklabels(heatmap_labels, rotation=45, ha='right', fontsize=9)
            ax2.set_yticklabels(heatmap_labels, fontsize=9)
            ax2.set_title('高相关特征热力图', fontsize=12, fontweight='bold')

            for i in range(len(heatmap_vars)):
                for j in range(len(heatmap_vars)):
                    val = heatmap_corr.iloc[i, j]
                    ax2.text(j, i, f'{val:.3f}', ha='center', va='center',
                             color='white' if abs(val) >= 0.5 else 'black', fontsize=8)

            cbar = plt.colorbar(im, ax=ax2, shrink=0.8)
            cbar.set_label('相关系数', fontsize=10)

    img_filename = f"{output_dir}{target_name}_相关性可视化图.png"
    plt.tight_layout()
    plt.savefig(img_filename, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

    high_count = len(corr_df[corr_df['相关性强度'] == '高相关'])
    mid_count = len(corr_df[corr_df['相关性强度'] == '中等相关'])
    low_count = len(corr_df[corr_df['相关性强度'] == '低相关'])


    return {
        '目标变量名称': target_name,  # 统一列名，避免KeyError
        '高相关特征数': high_count,
        '中等相关特征数': mid_count,
        '低相关特征数': low_count,
        'Excel文件': os.path.basename(excel_filename),
        '可视化文件': os.path.basename(img_filename)
    }


all_stats = []
for target in target_variables:
    stats = analyze_target(target, df_clean, valid_feature_cols, output_dir)
    all_stats.append(stats)

summary_df = pd.DataFrame(all_stats)
summary_df = pd.merge(
    summary_df,
    target_info_df[['目标变量名称', '均值(%)', '最大值(%)', '最小值(%)', '有效数据量']],
    on='目标变量名称'  # 确保关联列名完全一致，修复KeyError
)

# 调整汇总表列顺序，便于阅读
summary_df = summary_df[
    ['目标变量名称', '有效数据量', '均值(%)', '最大值(%)', '最小值(%)',
     '高相关特征数', '中等相关特征数', '低相关特征数', 'Excel文件', '可视化文件']
]

# 保存汇总报告（输出到../outputs/目录）
summary_report_path = f"{output_dir}5个目标变量相关性分析汇总报告.xlsx"
with pd.ExcelWriter(summary_report_path, engine='openpyxl') as writer:
    summary_df.to_excel(writer, sheet_name='汇总统计', index=False)
    target_info_df.to_excel(writer, sheet_name='目标变量基础信息', index=False)
    pd.DataFrame(valid_feature_cols, columns=['有效特征列表']).to_excel(writer, sheet_name='有效特征', index=False)


