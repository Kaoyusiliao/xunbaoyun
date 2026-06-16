# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import chi2_contingency, ttest_ind
import statsmodels.api as sm
from pyecharts.charts import Map
from pyecharts import options as opts
import warnings

warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-ticks')
plt.rcParams['font.sans-serif'] = ['Songti SC']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['legend.fontsize'] = 9

DB_PATH = "bbhj_under18.sql"
TABLE_NAME = "宝贝回家未成年"

# 省份提取与标准化
STANDARD_PROVINCES = [
    '北京', '天津', '上海', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江',
    '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南',
    '广东', '海南', '四川', '贵州', '云南', '陕西', '甘肃', '青海', '台湾',
    '内蒙古', '广西', '西藏', '宁夏', '新疆', '香港', '澳门'
]

PROVINCE_ALIAS = {
    '北京市': '北京', '天津市': '天津', '上海市': '上海', '重庆市': '重庆',
    '河北省': '河北', '山西省': '山西', '辽宁省': '辽宁', '吉林省': '吉林', '黑龙江省': '黑龙江',
    '江苏省': '江苏', '浙江省': '浙江', '安徽省': '安徽', '福建省': '福建', '江西省': '江西',
    '山东省': '山东', '河南省': '河南', '湖北省': '湖北', '湖南省': '湖南', '广东省': '广东',
    '海南省': '海南', '四川省': '四川', '贵州省': '贵州', '云南省': '云南', '陕西省': '陕西',
    '甘肃省': '甘肃', '青海省': '青海', '台湾省': '台湾',
    '内蒙古自治区': '内蒙古', '广西壮族自治区': '广西', '西藏自治区': '西藏',
    '宁夏回族自治区': '宁夏', '新疆维吾尔自治区': '新疆',
    '香港特别行政区': '香港', '澳门特别行政区': '澳门',
    '北京': '北京', '天津': '天津', '上海': '上海', '重庆': '重庆',
    '河北': '河北', '山西': '山西', '辽宁': '辽宁', '吉林': '吉林', '黑龙江': '黑龙江',
    '江苏': '江苏', '浙江': '浙江', '安徽': '安徽', '福建': '福建', '江西': '江西',
    '山东': '山东', '河南': '河南', '湖北': '湖北', '湖南': '湖南', '广东': '广东',
    '海南': '海南', '四川': '四川', '贵州': '贵州', '云南': '云南', '陕西': '陕西',
    '甘肃': '甘肃', '青海': '青海', '台湾': '台湾',
    '内蒙古': '内蒙古', '广西': '广西', '西藏': '西藏', '宁夏': '宁夏', '新疆': '新疆',
    '香港': '香港', '澳门': '澳门'
}
def extract_province(addr):
    if pd.isna(addr) or not isinstance(addr, str):
        return None
    if ',' in addr:
        main_part = addr.split(',')[0].strip()
    else:
        main_part = addr.strip()
    for alias in sorted(PROVINCE_ALIAS.keys(), key=len, reverse=True):
        if alias in main_part:
            return PROVINCE_ALIAS[alias]
    return None

# 分类关键词
RUNAWAY_KEYWORDS = [
    '离家出走', '离家', '出走', '厌学', '赌气', '见网友', '打工', '不想回家',
    '争吵', '负气', '跑', '赌气离家', '负气出走', '与家人争吵', '赌气出走',
    '离家未归', '离家失联', '离家后', '离家至今', '离家外出', '出走至今',
    '不想上学', '不想读书', '外出打工', '找工作', '叛逆','和爸妈吵','后来姐姐自己一个人走了',
    '违犯了课堂纪律被老师罚回家叫家长','不听爸爸妈妈的听！就打了她','他妈妈就骂了他','怕她爸打她','趁家人没起床 只留下一张纸条说'
]
TRAFFICK_KEYWORDS = [
    '拐卖', '被拐', '人贩子', '被带走', '卖到', '控制', '诱骗', '拐走', '拐骗',
    '被拐卖', '被拐走', '拐卖儿童', '被拐骗', '被人拐', '被陌生人带走','被偷',
    '诱拐', '绑架', '被绑架', '被强行带走', '骗', '拐', '被人', '盗','引诱','被船载走','强行',
    '被一个人抱','罪犯被抓','妈妈给人下药','被带走','带走','就是晚上有人叫门说是喝水，我妈就开门结果就被打了，我妈醒来弟弟就不在了','偷走','男子拿砖头打晕母亲，用毛巾塞嘴，抢走了小孩','抢走'
    ,'孩子放学回家，回家后有人敲门，家长回家后看到门口有个凳子，估计是看猫眼，看是熟人才开的门，走时书包还放在家里。有人看见孩子上了一两面包车后就再也没有音信','我们跟他们走一段路，我弟的鞋掉小沟里，我去捡抬头就看不见我弟了',
    '被俩人拉上了车','完了之后她抱起走了','等车时上了一辆面包车后就没消息','有个陌生男人住在家里','被一四川邻居假装抱去玩'
]
ABANDON_KEYWORDS = [
    '送养', '送人', '遗弃', '抱养', '被抱养', '弃婴', '被人抱走', '无（送养）',
    '无（遗弃）', '送', '抱走', '送掉', '丢弃', '被遗弃', '被送人', '被送养',
    '放弃抚养', '送他人', '送给', '送与','我爸妈生她下来因为家里穷，然后把她放到我们宜黄县福利院'
]
LOST_KEYWORDS = [
    '走失', '走丢', '迷路', '与家人走散', '迷失', '走散', '丢失', '失踪',
    '走失儿童', '走失人员', '走失至今', '外出未归', '失联', '不知去向', '丢','不小心','不见了',
    '遗失','不见人','没有注意孩子。约十一点左右开始寻找孩子便没有找到','她忘了带，就去厕所里躲一躲',
    '在那里被冲散了，直到现在也没有音信','找不到','至今不知下落','她外婆说他们已经上车走了,从此就没见了','一直没有联系','再未见人','跟小孩玩，因为自己比较落后，别的孩子都回家了，之后大人就开始找孩子！',
    '和一对双胞胎女孩一起到胡家园小学玩','下落不明','妹妹说去河边抓蝴蝶就在也没有回家','失去联系','失散'
]

def classify_subtype(row):
    text = str(row['失踪类型']) + " " + str(row['姓名']) + " " + str(row['失踪地址'])
    stripped = text.strip()
    if stripped == "":
        return '其他'
    lower_text = stripped.lower()
    for kw in RUNAWAY_KEYWORDS:
        if kw.lower() in lower_text:
            return '离家出走'
    for kw in TRAFFICK_KEYWORDS:
        if kw.lower() in lower_text:
            return '拐卖'
    for kw in LOST_KEYWORDS:
        if kw.lower() in lower_text:
            return '走失'
    for kw in ABANDON_KEYWORDS:
        if kw.lower() in lower_text:
            return '送养遗弃'
    return '未分类'

def load_and_clean():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", conn)
    conn.close()
    print(f"原始记录数: {len(df)}")

    required = ['失踪时间', '失踪地址', 'missing_age', '性别']
    before = len(df)
    df = df.dropna(subset=required)
    print(f"剔除缺失后: {len(df)} (删 {before - len(df)})")

    df['失踪时间'] = pd.to_datetime(df['失踪时间'], errors='coerce')
    before = len(df)
    df = df.dropna(subset=['失踪时间'])
    print(f"有效日期后: {len(df)} (删 {before - len(df)})")

    df['年份'] = df['失踪时间'].dt.year
    before = len(df)
    df = df[(df['年份'] >= 1960) & (df['年份'] <= 2026)]
    print(f"年份过滤后: {len(df)} (删 {before - len(df)})")

    before = len(df)
    df = df[df['missing_age'] < 18]
    print(f"未成年后: {len(df)} (删 {before - len(df)})")

    key_cols = ['姓名', '性别', '失踪时间', '失踪地址']
    df['_dup'] = df[key_cols].astype(str).agg('-'.join, axis=1)
    before = len(df)
    df = df.drop_duplicates(subset=['_dup'])
    df.drop('_dup', axis=1, inplace=True)
    print(f"去重后: {len(df)} (删 {before - len(df)})")

    if len(df) == 0:
        raise ValueError("无有效数据")

    df['月份'] = df['失踪时间'].dt.month
    df['星期'] = df['失踪时间'].dt.dayofweek
    df['是否周末'] = df['星期'].apply(lambda x: 1 if x >= 5 else 0)

    bins = [0, 6, 12, 18]
    labels = ['0-6岁', '7-12岁', '13-17岁']
    df['年龄分组'] = pd.cut(df['missing_age'], bins=bins, labels=labels, right=False)

    df['失踪亚类型'] = df.apply(classify_subtype, axis=1)
    print("\n=== 分类统计 ===")
    print(df['失踪亚类型'].value_counts())

    unmatched = df[df['失踪亚类型'] == '未分类']
    if len(unmatched) > 0:
        export_cols = ['id', '姓名', '性别', '失踪时间', '失踪类型', '失踪地址', 'missing_age']
        if 'id' not in unmatched.columns:
            unmatched['id'] = unmatched.index
        unmatched[export_cols].to_csv('unclassified_records.csv', index=False, encoding='utf-8-sig')
        print(f"\n⚠️ 发现 {len(unmatched)} 条未分类记录，已导出到 unclassified_records.csv")
    else:
        print("\n所有非空白记录均已分类！")

    df['省份'] = df['失踪地址'].apply(extract_province)
    print(f"\n成功提取省份的记录数: {df['省份'].notna().sum()}")
    if df['省份'].notna().sum() > 0:
        print("省份分布前10:")
        print(df['省份'].value_counts().head(10))
        unique_provs = df['省份'].dropna().unique()
        print("省份唯一值示例（前20）：", list(unique_provs)[:20])
        invalid = set(unique_provs) - set(STANDARD_PROVINCES)
        if invalid:
            print(f"警告：以下省份不在 pyecharts 标准名称中，地图上将不显示：{invalid}")
    else:
        print("警告：未提取到任何省份！请检查地址字段内容。")

    def is_holiday(date):
        if (date.month == 1 and date.day >= 15) or (date.month == 2 and date.day <= 25):
            return 1
        if (date.month == 9 and date.day >= 24) or (date.month == 10 and date.day <= 8):
            return 1
        return 0
    df['是否节假日'] = df['失踪时间'].apply(is_holiday)

    return df

# 图表函数
def add_source_note(fig, text="数据来源：宝贝回家网", x=0.99, y=0.01):
    fig.text(x, y, text, fontsize=8, ha='right', va='bottom', style='italic',
             transform=fig.transFigure, bbox=dict(boxstyle='round', facecolor='white', alpha=0.6))

def plot_time_trend(df):
    # 总数图
    year_total = df.groupby('年份').size().reset_index(name='总数')
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(year_total['年份'], year_total['总数'], marker='o', color='#333333', linewidth=1.5, markersize=4)
    ax.set_title('历年失踪总数 (1960-2026)')
    ax.set_xlabel('年份')
    ax.set_ylabel('案例数')
    ax.grid(True, linestyle='--', alpha=0.6)
    add_source_note(fig)
    plt.tight_layout()
    fig.savefig('时间趋势_总数.png', dpi=300)
    fig.savefig('时间趋势_总数.pdf', format='pdf')
    plt.show()
    print("已保存: 时间趋势_总数.png 和 .pdf")
    plt.close(fig)

    # 亚类型图
    subtype_list = ['离家出走', '拐卖', '送养遗弃', '走失', '未分类']
    colors = ['#0072B2', '#E69F00', '#009E73', '#D55E00', '#CC79A7']
    for st, color in zip(subtype_list, colors):
        data = df[df['失踪亚类型'] == st].groupby('年份').size().reset_index(name='数量')
        if data.empty:
            print(f"跳过 {st}，无数据")
            continue
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(data['年份'], data['数量'], marker='o', color=color, linewidth=1.5, markersize=4)
        ax.set_title(f'{st}历年失踪数量 (1960-2026)')
        ax.set_xlabel('年份')
        ax.set_ylabel('案例数')
        ax.grid(True, linestyle='--', alpha=0.6)
        add_source_note(fig)
        plt.tight_layout()
        safe_st = st.replace('送养遗弃', '送养遗弃')
        filename_png = f'时间趋势_{safe_st}.png'
        filename_pdf = f'时间趋势_{safe_st}.pdf'
        fig.savefig(filename_png, dpi=300)
        fig.savefig(filename_pdf, format='pdf')
        plt.show()
        print(f"已保存: {filename_png} 和 {filename_pdf}")
        plt.close(fig)

def plot_spatial_bar(df):
    prov_counts = df[df['省份'].notna()].groupby('省份').size().reset_index(name='数量')
    if prov_counts.empty:
        print("无省份信息，跳过条形图")
        return
    prov_counts = prov_counts.sort_values('数量', ascending=False)
    fig, ax = plt.subplots(figsize=(12, 8))
    sns.barplot(data=prov_counts, x='数量', y='省份', palette='Reds_r', ax=ax)
    ax.set_title('各省份未成年失踪案例数量分布')
    ax.set_xlabel('失踪案例数')
    ax.set_ylabel('省份')
    add_source_note(fig)
    plt.tight_layout()
    fig.savefig('省份分布图.png', dpi=300)
    fig.savefig('省份分布图.pdf', format='pdf')
    plt.show()
    prov_counts.to_csv('省份分布数据.csv', index=False, encoding='utf-8-sig')
    print("已保存: 省份分布图.png, .pdf 和 省份分布数据.csv")
    plt.close(fig)

def plot_spatial_map(df):
    prov_counts = df[df['省份'].notna()].groupby('省份').size().reset_index(name='数量')
    if prov_counts.empty:
        print("无省份信息，跳过地图生成")
        return
    prov_counts = prov_counts[prov_counts['省份'].isin(STANDARD_PROVINCES)]
    if prov_counts.empty:
        print("没有符合标准名称的省份数据，地图无法生成")
        return
    map_data = list(zip(prov_counts['省份'].tolist(), prov_counts['数量'].tolist()))
    c = (Map()
         .add("失踪案例数", map_data, "china")
         .set_global_opts(
             title_opts=opts.TitleOpts(title="中国未成年失踪案例省级分布 (1960-2026)"),
             visualmap_opts=opts.VisualMapOpts(
                 min_=prov_counts['数量'].min(),
                 max_=prov_counts['数量'].max(),
                 range_color=["#e0f3f8", "#abd9e9", "#74add1", "#4575b4", "#313695"]
             )
         )
    )
    c.render("省级分布色斑图.html")
    print("已生成交互式地图：省级分布色斑图.html（请用浏览器打开）")

def plot_age_distribution(df):
    print("\n各亚类型年龄统计（用于箱线图）:")
    for subtype in df['失踪亚类型'].unique():
        age_data = df[df['失踪亚类型']==subtype]['missing_age'].dropna()
        print(f"{subtype}: 样本量={len(age_data)}, 均值={age_data.mean():.2f}, 中位数={age_data.median():.2f}")

    unique_types = df['失踪亚类型'].unique()
    print("所有亚类型：", unique_types)

    # 定义顺序（使用修改后的名称）
    order_raw = ['离家出走', '拐卖', '送养遗弃', '走失', '其他', '未分类']
    order_raw = [c for c in order_raw if c in unique_types]
    
    if len(order_raw) == 0:
        print("无有效分类数据，跳过箱线图")
        return

    fig, axes = plt.subplots(1, 2, figsize=(18, 6))
    # 左图：年龄直方图
    sns.histplot(df['missing_age'], bins=30, kde=True, ax=axes[0], color='skyblue')
    axes[0].set_title('总体年龄分布')
    axes[0].set_xlabel('年龄')
    axes[0].set_ylabel('频次')

    # 右图：箱线图（直接使用原始名称，已经没有斜杠）
    sns.boxplot(data=df, x='失踪亚类型', y='missing_age', order=order_raw, ax=axes[1], palette='Set2')
    axes[1].set_title('分失踪亚类型的年龄分布箱线图')
    axes[1].set_xlabel('失踪亚类型')
    axes[1].set_ylabel('年龄')
    axes[1].tick_params(axis='x', rotation=45)
    fig.subplots_adjust(bottom=0.25)

    add_source_note(fig)
    plt.tight_layout()
    fig.savefig('年龄分布图.png', dpi=300)
    fig.savefig('年龄分布图.pdf', format='pdf')
    plt.show()
    print("已保存: 年龄分布图.png 和 .pdf")
    plt.close(fig)

def plot_gender_ratio(df):
    ct = pd.crosstab(df['失踪亚类型'], df['性别'])
    order = ['离家出走', '拐卖', '送养遗弃', '走失', '其他', '未分类']
    ct = ct.reindex([x for x in order if x in ct.index])
    fig, ax = plt.subplots(figsize=(10,6))
    ct.plot(kind='bar', ax=ax, color=['#66c2a5','#fc8d62'], edgecolor='black')
    ax.set_title('各失踪亚类型的性别分布 (p<0.001, 卡方检验)')
    ax.set_xlabel('失踪亚类型')
    ax.set_ylabel('案例数')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    ax.legend(title='性别')
    for container in ax.containers:
        ax.bar_label(container, label_type='edge', fontsize=9)
    add_source_note(fig)
    plt.tight_layout()
    fig.savefig('性别比例.png', dpi=300)
    fig.savefig('性别比例.pdf', format='pdf')
    plt.show()
    print("已保存: 性别比例.png 和 .pdf")
    if len(ct) > 1:
        chi2, p, dof, ex = chi2_contingency(ct)
        print(f"各亚类型性别构成卡方检验: chi2={chi2:.4f}, p={p:.6f}")
    plt.close(fig)

def plot_holiday_effect(df):
    daily = df.groupby('失踪时间').size().reset_index(name='日失踪数')
    daily['是否节假日'] = daily['失踪时间'].apply(
        lambda d: 1 if (d.month==1 and d.day>=15) or (d.month==2 and d.day<=25) or (d.month==9 and d.day>=24) or (d.month==10 and d.day<=8) else 0)
    avg = daily.groupby('是否节假日')['日失踪数'].mean().reset_index()
    avg['类型'] = avg['是否节假日'].map({0:'非节假日',1:'节假日'})
    fig, ax = plt.subplots(figsize=(6,4))
    sns.barplot(data=avg, x='类型', y='日失踪数', palette=['skyblue','salmon'], ax=ax)
    ax.set_title('节假日 vs 非节假日日均失踪数 (p<0.001, IRR=0.889)')
    ax.set_ylabel('日均失踪数')
    ax.grid(axis='y', linestyle='--')
    add_source_note(fig)
    plt.tight_layout()
    fig.savefig('节假日效应.png', dpi=300)
    fig.savefig('节假日效应.pdf', format='pdf')
    plt.show()
    X = sm.add_constant(daily['是否节假日'])
    y = daily['日失踪数']
    model = sm.GLM(y, X, family=sm.families.Poisson()).fit()
    print("\n节假日效应 Poisson回归:")
    print(model.summary())
    print(f"节假日系数={model.params['是否节假日']:.4f}, IRR={np.exp(model.params['是否节假日']):.4f}")
    print("已保存: 节假日效应.png 和 .pdf")
    plt.close(fig)

def plot_weekend_effect(df):
    daily = df.groupby('失踪时间').size().reset_index(name='日失踪数')
    daily['是否周末'] = daily['失踪时间'].dt.dayofweek.apply(lambda x: 1 if x>=5 else 0)
    avg = daily.groupby('是否周末')['日失踪数'].mean().reset_index()
    avg['类型'] = avg['是否周末'].map({0:'工作日',1:'周末'})
    fig, ax = plt.subplots(figsize=(6,4))
    sns.barplot(data=avg, x='类型', y='日失踪数', palette=['#66c2a5','#fc8d62'], ax=ax)
    ax.set_title('周末 vs 工作日日均失踪数 (p=0.158, 无显著差异)')
    ax.set_ylabel('日均失踪数')
    ax.grid(axis='y', linestyle='--')
    add_source_note(fig)
    plt.tight_layout()
    fig.savefig('星期效应.png', dpi=300)
    fig.savefig('星期效应.pdf', format='pdf')
    plt.show()
    weekdays = daily[daily['是否周末']==0]['日失踪数']
    weekends = daily[daily['是否周末']==1]['日失踪数']
    t, p = ttest_ind(weekdays, weekends)
    print(f"\n周末 vs 工作日 t检验: t={t:.4f}, p={p:.6f}")
    print("已保存: 星期效应.png 和 .pdf")
    plt.close(fig)

def main():
    try:
        df = load_and_clean()
        # 在运行完 load_and_clean() 后添加
        print("送养遗弃年龄描述：")
        print(df[df['失踪亚类型'] == '送养遗弃']['missing_age'].describe())
        print("唯一年龄值：", df[df['失踪亚类型'] == '送养遗弃']['missing_age'].unique()[:20])
    except Exception as e:
        print(f"错误: {e}")
        return
    plot_time_trend(df)
    plot_spatial_bar(df)
    plot_spatial_map(df)
    plot_age_distribution(df)
    plot_gender_ratio(df)
    plot_holiday_effect(df)
    plot_weekend_effect(df)
    print("\n全部完成！")

if __name__ == "__main__":
    main()