#!/usr/bin/env python3
"""Generate the TASK5 course-stock classification analysis notebook."""

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "Task5" / "course_stock_classification.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


def main() -> None:
    notebook = nbf.v4.new_notebook()
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"},
    }
    notebook["cells"] = [
        md(
            """
# TASK5 股票季度分类模型

## 结论摘要

本Notebook使用课程股票数据，将样本单位固定为“某只股票在某个季度末”。应变量是下一季度收益率是否大于0；自变量由当期估值与规模、滞后一季度的财务增长以及上一季度已实现收益构成。所有特征选择和调参只使用2020—2021年数据，2022年只做最终时间外检验。

Notebook执行后，以下表格和图形给出实际的特征筛选、模型表现与概率分组结果。
"""
        ),
        md(
            r"""
## 一、研究问题与X/Y定义

### 应变量Y

\[
Y_{i,t}=1\left(Next\_Ret_{i,t}>0\right)
\]

`Next_Ret` 是股票 *i* 从季度末 *t* 到下一季度末的收益率。模型输出的是下一季度收益为正的估计概率，而不是预测收益率数值。

### 候选自变量X

- **当期可观察估值与规模（9项）**：EV/EBITDA、PB、两种PCF、PE、扣非PE、PS、股息率和对数市值。
- **滞后一季度的财务增长（8项）**：净利润、净资产、利润总额、EPS、总资产、现金净流量、营业利润和营业总收入同比增长率。滞后处理是为了降低财报在报告期末尚未公布的未来信息风险。
- **历史价格特征（2项）**：上一季度已实现收益率和其绝对值，分别表示粗粒度动量与价格冲击幅度。

`Date` 和 `Code` 只是样本标识，不作为模型特征。由于课程文件没有公告日期和日频价格，本分析无法构造更细的RSI、MACD和日频波动率。
"""
        ),
        md("## 二、数据加载与质量检查"),
        code(
            """
from pathlib import Path
import json
import warnings

warnings.filterwarnings("ignore")

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from IPython.display import display
from scipy.stats import pointbiserialr
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score,
    brier_score_loss, confusion_matrix, f1_score, precision_score,
    recall_score, roc_auc_score, roc_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

pd.set_option("display.max_columns", 50)
pd.set_option("display.float_format", lambda value: f"{value:.4f}")
sns.set_theme(style="whitegrid", context="notebook")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Songti SC", "STSong", "Arial Unicode MS", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "figure.dpi": 120,
})

RANDOM_STATE = 42
START = Path.cwd().resolve()
ROOT = START if (START / "Task6" / "data" / "model_data.csv").exists() else START.parent
COURSE_PATH = ROOT / "Task6" / "data" / "model_data.csv"
CLASS_PATH = ROOT / "Task6" / "inputs" / "model_data_stock.csv"
OUTPUT_DIR = ROOT / "data" / "task5" / "course_model" / "processed"
MODEL_DIR = OUTPUT_DIR / "models"
CHART_DIR = ROOT / "artifacts" / "charts" / "task5" / "course_model"
for directory in [OUTPUT_DIR, MODEL_DIR, CHART_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

raw = pd.read_csv(COURSE_PATH)
raw["Date"] = pd.to_datetime(raw["Date"])
raw["Code"] = raw["Code"].astype(str).str.zfill(6)
raw = raw.sort_values(["Code", "Date"]).reset_index(drop=True)

course_class = pd.read_csv(CLASS_PATH)
course_class["Date"] = pd.to_datetime(course_class["Date"])
course_class["Code"] = course_class["Code"].astype(str).str.zfill(6)

quality_summary = pd.DataFrame({
    "检查项": ["记录数", "列数", "季度数", "股票数", "最早季度", "最晚季度", "Date+Code重复数", "缺失单元格", "Next_Ret非有限数"],
    "结果": [len(raw), raw.shape[1], raw["Date"].nunique(), raw["Code"].nunique(), raw["Date"].min().date(), raw["Date"].max().date(), raw.duplicated(["Date", "Code"]).sum(), raw.isna().sum().sum(), (~np.isfinite(raw["Next_Ret"])).sum()],
})
print("表1：课程完整数据质量概览")
display(quality_summary)

label_check = course_class[["Date", "Code", "Y"]].merge(
    raw[["Date", "Code", "Next_Ret"]], on=["Date", "Code"], how="left", validate="one_to_one"
)
label_agreement = (label_check["Y"] == label_check["Next_Ret"].gt(0)).mean()
print(f"分类文件与 Y=(Next_Ret>0) 的逐行符合率：{label_agreement:.2%}")
assert raw.duplicated(["Date", "Code"]).sum() == 0
assert raw.isna().sum().sum() == 0
assert label_agreement == 1
"""
        ),
        md("## 三、构造时间可用的混合特征"),
        code(
            """
VALUATION_MAP = {
    "ev_ebitda": "企业倍数(EV除EBITDA)",
    "pb": "市净率PB(MRQ)",
    "pcf_net": "市现率PCF(现金净流量TTM)",
    "pcf_oper": "市现率PCF(经营现金流TTM)",
    "pe": "市盈率PE(TTM)",
    "pe_adj": "市盈率PE(TTM,扣除非经常性损益)",
    "ps": "市销率PS(TTM)",
    "dividend_yield": "股息率(近12个月)",
    "mv": "MV",
}
FINANCIAL_MAP = {
    "net_profit_growth": "净利润同比增长率",
    "equity_growth": "净资产同比增长率",
    "total_profit_growth": "利润总额(同比增长率)",
    "eps_growth": "基本每股收益(同比增长率)",
    "assets_growth": "总资产同比增长率",
    "net_cash_growth": "现金净流量同比增长率",
    "operating_profit_growth": "营业利润(同比增长率)",
    "revenue_growth": "营业总收入(同比增长率)",
}

current = raw[["Date", "Code", "Next_Ret"] + list(VALUATION_MAP.values())].copy()
for short_name, source_name in VALUATION_MAP.items():
    current[short_name] = current[source_name]
current["log_mv"] = np.log1p(current["mv"].clip(lower=0))
current = current.drop(columns=list(VALUATION_MAP.values()) + ["mv"])

# 把上一季度整行数据平移到下一个季度末，只有连续季度才能匹配。
lagged = raw[["Date", "Code", "Next_Ret"] + list(FINANCIAL_MAP.values())].copy()
lagged["Date"] = lagged["Date"] + pd.offsets.QuarterEnd(1)
for short_name, source_name in FINANCIAL_MAP.items():
    lagged[f"{short_name}_lag1"] = lagged[source_name]
lagged["ret_1q"] = lagged["Next_Ret"]
lagged["abs_ret_1q"] = lagged["Next_Ret"].abs()
lagged = lagged.drop(columns=["Next_Ret"] + list(FINANCIAL_MAP.values()))

dataset = current.merge(lagged, on=["Date", "Code"], how="left", validate="one_to_one")
dataset = dataset.loc[dataset["Date"] > raw["Date"].min()].copy()
dataset["Y"] = dataset["Next_Ret"].gt(0).astype(int)

VALUATION_FEATURES = [
    "ev_ebitda", "pb", "pcf_net", "pcf_oper", "pe", "pe_adj", "ps", "dividend_yield", "log_mv"
]
FINANCIAL_FEATURES = [f"{name}_lag1" for name in FINANCIAL_MAP]
TECHNICAL_FEATURES = ["ret_1q", "abs_ret_1q"]
CANDIDATE_FEATURES = VALUATION_FEATURES + FINANCIAL_FEATURES + TECHNICAL_FEATURES

FEATURE_LABELS = {
    "ev_ebitda": "EV/EBITDA", "pb": "PB", "pcf_net": "PCF-净现金流", "pcf_oper": "PCF-经营现金流",
    "pe": "PE", "pe_adj": "扣非PE", "ps": "PS", "dividend_yield": "股息率", "log_mv": "对数市值",
    "net_profit_growth_lag1": "滞后净利润增长", "equity_growth_lag1": "滞后净资产增长",
    "total_profit_growth_lag1": "滞后利润总额增长", "eps_growth_lag1": "滞后EPS增长",
    "assets_growth_lag1": "滞后总资产增长", "net_cash_growth_lag1": "滞后现金净流增长",
    "operating_profit_growth_lag1": "滞后营业利润增长", "revenue_growth_lag1": "滞后营收增长",
    "ret_1q": "上季度收益", "abs_ret_1q": "上季度收益绝对值",
}

# 保留一份未做截面分位数转换的数据，用于描述统计和原始分布展示。
raw_feature_snapshot = dataset[["Date", "Code", "Next_Ret", "Y"] + CANDIDATE_FEATURES].copy()

# 转换为同季度截面分位数，降低负估值、极端财务增长率和规模差异的影响。
for feature in CANDIDATE_FEATURES:
    dataset[feature] = dataset.groupby("Date")[feature].rank(pct=True, method="average")

print(f"建模数据：{len(dataset):,}行，{dataset['Code'].nunique():,}只股票，{dataset['Date'].nunique()}个季度，{len(CANDIDATE_FEATURES)}个候选特征")
missing_summary = dataset[CANDIDATE_FEATURES].isna().mean().sort_values(ascending=False).rename("缺失率").to_frame()
display(missing_summary.head(10))
"""
        ),
        md("## 四、Y分布、描述统计与分组分析"),
        code(
            """
quarter_summary = dataset.groupby("Date", as_index=False).agg(
    样本数=("Code", "size"), 股票数=("Code", "nunique"), 正收益样本=("Y", "sum"), 正样本比例=("Y", "mean"), 平均下季度收益=("Next_Ret", "mean")
)
print("表2：分季度样本和Y分布")
display(quarter_summary)

fig, axes = plt.subplots(1, 2, figsize=(12, 4.3))
sns.countplot(data=dataset, x="Y", color="#C87500", ax=axes[0])
axes[0].set(title="图1aY总体分布", xlabel="Y（0=下季度非正收益，1=正收益）", ylabel="样本数")
sns.barplot(data=quarter_summary, x="Date", y="正样本比例", color="#D9902F", ax=axes[1])
axes[1].axhline(0.5, color="#666666", linestyle="--", linewidth=1)
axes[1].set(title="图2：各季度Y=1的比例", xlabel="季度末", ylabel="正样本比例", ylim=(0, 0.8))
axes[1].tick_params(axis="x", rotation=45)
plt.tight_layout()
plt.savefig(CHART_DIR / "label_distribution.png", bbox_inches="tight")
plt.show()
"""
        ),
        code(
            """
DEVELOPMENT_END = pd.Timestamp("2021-12-31")
TEST_START = pd.Timestamp("2022-03-31")
development = dataset.loc[dataset["Date"] <= DEVELOPMENT_END].copy()
test = dataset.loc[dataset["Date"] >= TEST_START].copy()
raw_development = raw_feature_snapshot.loc[raw_feature_snapshot["Date"] <= DEVELOPMENT_END].copy()

descriptive = raw_development[CANDIDATE_FEATURES].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]).T
descriptive["缺失率"] = raw_development[CANDIDATE_FEATURES].isna().mean()
descriptive.index = [FEATURE_LABELS[name] for name in descriptive.index]
print("表3：候选特征原始值描述统计（2020年6月至2021年12月）")
display(descriptive)

group_rows = []
for feature in CANDIDATE_FEATURES:
    part = development[[feature, "Y"]].dropna()
    y0 = part.loc[part["Y"] == 0, feature]
    y1 = part.loc[part["Y"] == 1, feature]
    pooled_std = np.sqrt((y0.var(ddof=1) + y1.var(ddof=1)) / 2)
    correlation = pointbiserialr(part["Y"], part[feature]).statistic if part[feature].nunique() > 1 else np.nan
    univariate_auc = roc_auc_score(part["Y"], part[feature]) if part[feature].nunique() > 1 else np.nan
    group_rows.append({
        "feature": feature, "特征": FEATURE_LABELS[feature], "Y=0均值": y0.mean(), "Y=1均值": y1.mean(),
        "Y=0中位数": y0.median(), "Y=1中位数": y1.median(),
        "标准化均值差": (y1.mean() - y0.mean()) / pooled_std if pooled_std > 0 else np.nan,
        "点二列相关": correlation, "单变量AUC(原方向)": univariate_auc,
    })
grouped_analysis = pd.DataFrame(group_rows).sort_values("点二列相关", key=lambda s: s.abs(), ascending=False)
print("表4：按Y分组的描述性分析（仅开发期）")
display(grouped_analysis.drop(columns="feature"))
"""
        ),
        md("## 五、相关性、滚动稳定性和VIF筛选"),
        code(
            """
corr = development[CANDIDATE_FEATURES].corr()
plt.figure(figsize=(13, 10))
sns.heatmap(corr, cmap="RdBu_r", center=0, vmin=-1, vmax=1, square=True, linewidths=0.25,
            xticklabels=[FEATURE_LABELS[f] for f in CANDIDATE_FEATURES],
            yticklabels=[FEATURE_LABELS[f] for f in CANDIDATE_FEATURES])
plt.title("图3：候选特征相关系数热力图（仅开发期）")
plt.tight_layout()
plt.savefig(CHART_DIR / "candidate_correlation_heatmap.png", bbox_inches="tight")
plt.show()

high_corr_pairs = []
for i, left in enumerate(CANDIDATE_FEATURES):
    for right in CANDIDATE_FEATURES[i + 1:]:
        if abs(corr.loc[left, right]) >= 0.80:
            high_corr_pairs.append({"特征1": FEATURE_LABELS[left], "特征2": FEATURE_LABELS[right], "相关系数": corr.loc[left, right]})
print("表5：绝对相关系数不低于0.80的特征对")
display(pd.DataFrame(high_corr_pairs).sort_values("相关系数", key=lambda s: s.abs(), ascending=False))
"""
        ),
        code(
            """
development_dates = sorted(development["Date"].unique())
walk_forward_folds = [(development_dates[:index], [development_dates[index]]) for index in range(3, len(development_dates))]

def make_logistic(c_value=0.1):
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(C=c_value, max_iter=3000, random_state=RANDOM_STATE)),
    ])

screen_rows = []
for feature in CANDIDATE_FEATURES:
    fold_aucs = []
    fold_signs = []
    for train_dates, validation_dates in walk_forward_folds:
        train_fold = development.loc[development["Date"].isin(train_dates)]
        validation_fold = development.loc[development["Date"].isin(validation_dates)]
        univariate_model = make_logistic(0.1)
        univariate_model.fit(train_fold[[feature]], train_fold["Y"])
        probability = univariate_model.predict_proba(validation_fold[[feature]])[:, 1]
        fold_aucs.append(roc_auc_score(validation_fold["Y"], probability))
        fold_signs.append(np.sign(univariate_model.named_steps["model"].coef_[0, 0]))
    dominant_sign = np.sign(np.median(fold_signs))
    screen_rows.append({
        "feature": feature, "特征": FEATURE_LABELS[feature],
        "滚动验证平均AUC": np.mean(fold_aucs), "AUC标准差": np.std(fold_aucs),
        "方向一致折数": int(np.sum(np.array(fold_signs) == dominant_sign)),
        **{f"验证折{i + 1}AUC": value for i, value in enumerate(fold_aucs)},
    })
screening = pd.DataFrame(screen_rows).sort_values(["方向一致折数", "滚动验证平均AUC"], ascending=False)
print("表6：候选特征滚动验证结果")
display(screening.drop(columns="feature"))

# 先按方向稳定性和验证AUC排序，再在高相关特征中只保留一个，最多保留8项。
ordered_candidates = screening["feature"].tolist()
selected_features = []
drop_reasons = {}
for feature in ordered_candidates:
    correlated_with = [kept for kept in selected_features if abs(corr.loc[feature, kept]) >= 0.80]
    if correlated_with:
        drop_reasons[feature] = f"与{FEATURE_LABELS[correlated_with[0]]}高相关"
    elif len(selected_features) < 8:
        selected_features.append(feature)
    else:
        drop_reasons[feature] = "超过8项简洁性上限"

def vif_table(frame, features):
    imputed = frame[features].copy().fillna(frame[features].median())
    standardized = StandardScaler().fit_transform(imputed)
    with_constant = np.column_stack([np.ones(len(standardized)), standardized])
    return pd.DataFrame({
        "feature": features,
        "VIF": [variance_inflation_factor(with_constant, index) for index in range(1, with_constant.shape[1])],
    }).sort_values("VIF", ascending=False)

vif_before = vif_table(development, selected_features)
while len(selected_features) > 5 and vif_before["VIF"].max() > 5:
    feature_to_drop = vif_before.iloc[0]["feature"]
    drop_reasons[feature_to_drop] = "VIF大于5"
    selected_features.remove(feature_to_drop)
    vif_before = vif_table(development, selected_features)

vif_final = vif_table(development, selected_features)
selection_table = screening[["feature", "特征", "滚动验证平均AUC", "AUC标准差", "方向一致折数"]].copy()
selection_table["是否保留"] = selection_table["feature"].isin(selected_features)
selection_table["决定理由"] = selection_table["feature"].map(drop_reasons).fillna("保留")
print(f"最终保留{len(selected_features)}项特征：{[FEATURE_LABELS[f] for f in selected_features]}")
print("表7：特征筛选决定")
display(selection_table.drop(columns="feature"))
print("表8：最终特征VIF")
vif_display = vif_final.assign(特征=vif_final["feature"].map(FEATURE_LABELS))[["特征", "VIF"]]
display(vif_display)

screening.to_csv(OUTPUT_DIR / "feature_screening.csv", index=False, encoding="utf-8-sig")
vif_final.to_csv(OUTPUT_DIR / "selected_feature_vif.csv", index=False, encoding="utf-8-sig")
"""
        ),
        code(
            """
n_features = len(selected_features)
ncols = 2
nrows = int(np.ceil(n_features / ncols))
fig, axes = plt.subplots(nrows, ncols, figsize=(12, 3.2 * nrows))
axes = np.array(axes).reshape(-1)
boxplot_frame = raw_development[["Y"] + selected_features].copy()
for feature in selected_features:
    lower, upper = boxplot_frame[feature].quantile([0.01, 0.99])
    boxplot_frame[feature] = boxplot_frame[feature].clip(lower, upper)
for axis, feature in zip(axes, selected_features):
    sns.boxplot(data=boxplot_frame, x="Y", y=feature, color="#E3A34A", showfliers=False, ax=axis)
    axis.set(title=FEATURE_LABELS[feature], xlabel="Y", ylabel="原始值（1%—99%截尾展示）")
for axis in axes[n_features:]:
    axis.axis("off")
fig.suptitle("图4：最终特征原始值按Y分组的箱线图（仅开发期）", y=1.01, fontsize=14)
plt.tight_layout()
plt.savefig(CHART_DIR / "selected_feature_boxplots.png", bbox_inches="tight")
plt.show()
"""
        ),
        md("## 六、时间划分与模型训练"),
        code(
            """
split_summary = pd.DataFrame([
    {"分段": "开发期", "起始": development["Date"].min(), "截止": development["Date"].max(), "季度数": development["Date"].nunique(), "样本数": len(development), "股票数": development["Code"].nunique(), "Y=1比例": development["Y"].mean()},
    {"分段": "最终测试期", "起始": test["Date"].min(), "截止": test["Date"].max(), "季度数": test["Date"].nunique(), "样本数": len(test), "股票数": test["Code"].nunique(), "Y=1比例": test["Y"].mean()},
])
print("表9：时间划分与样本量")
display(split_summary)

timeline = dataset.groupby("Date", as_index=False).agg(样本数=("Code", "size"), 正样本比例=("Y", "mean"))
timeline["分段"] = np.where(timeline["Date"] <= DEVELOPMENT_END, "开发期", "最终测试期")
plt.figure(figsize=(11, 4.5))
sns.barplot(data=timeline, x="Date", y="样本数", hue="分段", palette={"开发期": "#A9A9A9", "最终测试期": "#C87500"})
plt.title("图5：不打乱时间的开发期与最终测试期")
plt.xlabel("季度末")
plt.ylabel("股票—季度样本数")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(CHART_DIR / "time_split.png", bbox_inches="tight")
plt.show()
"""
        ),
        code(
            """
MODEL_GRIDS = {
    "逻辑回归": [
        (f"C={c}", make_logistic(c)) for c in [0.03, 0.1, 0.3, 1.0]
    ],
    "决策树": [
        (f"depth={depth}, leaf={leaf}", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", DecisionTreeClassifier(max_depth=depth, min_samples_leaf=leaf, random_state=RANDOM_STATE)),
        ]))
        for depth in [2, 3, 4] for leaf in [100, 250]
    ],
    "随机森林": [
        (f"depth={depth}, leaf={leaf}", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestClassifier(n_estimators=250, max_depth=depth, min_samples_leaf=leaf,
                                              max_features="sqrt", n_jobs=-1, random_state=RANDOM_STATE)),
        ]))
        for depth in [3, 5] for leaf in [50, 150]
    ],
    "梯度提升": [
        (f"estimators={estimators}, depth={depth}", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", GradientBoostingClassifier(n_estimators=estimators, learning_rate=0.05, max_depth=depth,
                                                  min_samples_leaf=100, random_state=RANDOM_STATE)),
        ]))
        for estimators in [80, 150] for depth in [1, 2]
    ],
}

best_models = {}
tuning_rows = []
for model_name, candidates in MODEL_GRIDS.items():
    best_result = None
    for parameter_label, estimator in candidates:
        fold_aucs = []
        for train_dates, validation_dates in walk_forward_folds:
            train_fold = development.loc[development["Date"].isin(train_dates)]
            validation_fold = development.loc[development["Date"].isin(validation_dates)]
            fold_model = clone(estimator)
            fold_model.fit(train_fold[selected_features], train_fold["Y"])
            fold_probability = fold_model.predict_proba(validation_fold[selected_features])[:, 1]
            fold_aucs.append(roc_auc_score(validation_fold["Y"], fold_probability))
        tuning_rows.append({"模型": model_name, "参数": parameter_label, "滚动验证平均AUC": np.mean(fold_aucs), "AUC标准差": np.std(fold_aucs)})
        if best_result is None or np.mean(fold_aucs) > best_result[0]:
            best_result = (np.mean(fold_aucs), parameter_label, estimator)
    best_models[model_name] = {"验证AUC": best_result[0], "参数": best_result[1], "estimator": clone(best_result[2])}

tuning_results = pd.DataFrame(tuning_rows)
print("表10：各模型最优滚动验证参数")
display(tuning_results.sort_values(["模型", "滚动验证平均AUC"], ascending=[True, False]).groupby("模型").head(1))
"""
        ),
        md("## 七、最终测试集预测与评估"),
        code(
            """
metric_rows = []
prediction_frames = []
roc_frames = []
confusion_matrices = {}

for model_name, model_info in best_models.items():
    estimator = model_info["estimator"]
    estimator.fit(development[selected_features], development["Y"])
    probability = estimator.predict_proba(test[selected_features])[:, 1]
    prediction = (probability >= 0.5).astype(int)
    fpr, tpr, _ = roc_curve(test["Y"], probability)
    metric_rows.append({
        "模型": model_name, "最优参数": model_info["参数"], "滚动验证AUC": model_info["验证AUC"],
        "测试AUC": roc_auc_score(test["Y"], probability), "PR-AUC": average_precision_score(test["Y"], probability),
        "Accuracy": accuracy_score(test["Y"], prediction), "Balanced Accuracy": balanced_accuracy_score(test["Y"], prediction),
        "Precision": precision_score(test["Y"], prediction, zero_division=0), "Recall": recall_score(test["Y"], prediction, zero_division=0),
        "F1": f1_score(test["Y"], prediction, zero_division=0), "Brier": brier_score_loss(test["Y"], probability),
    })
    prediction_frames.append(pd.DataFrame({
        "Date": test["Date"].to_numpy(), "Code": test["Code"].to_numpy(), "Next_Ret": test["Next_Ret"].to_numpy(),
        "Y": test["Y"].to_numpy(), "model": model_name, "probability": probability, "prediction": prediction,
    }))
    roc_frames.append(pd.DataFrame({"model": model_name, "fpr": fpr, "tpr": tpr}))
    confusion_matrices[model_name] = confusion_matrix(test["Y"], prediction)
    joblib.dump(estimator, MODEL_DIR / f"{model_name}.joblib")

model_metrics = pd.DataFrame(metric_rows).sort_values("测试AUC", ascending=False)
test_predictions = pd.concat(prediction_frames, ignore_index=True)
roc_points = pd.concat(roc_frames, ignore_index=True)
print("表11：四种模型最终测试结果")
display(model_metrics)

model_metrics.to_csv(OUTPUT_DIR / "model_metrics.csv", index=False, encoding="utf-8-sig")
test_predictions.to_csv(OUTPUT_DIR / "test_predictions.csv", index=False, encoding="utf-8-sig")
roc_points.to_csv(OUTPUT_DIR / "roc_points.csv", index=False, encoding="utf-8-sig")

quarter_metric_rows = []
for (model_name, quarter), part in test_predictions.groupby(["model", "Date"]):
    quarter_metric_rows.append({
        "模型": model_name, "季度末": quarter, "样本数": len(part), "Y=1比例": part["Y"].mean(),
        "季度内AUC": roc_auc_score(part["Y"], part["probability"]), "平均预测概率": part["probability"].mean(),
    })
quarter_metrics = pd.DataFrame(quarter_metric_rows)
print("表11A：分季度测试AUC与概率水平")
display(quarter_metrics)

development_prevalence = development["Y"].mean()
constant_probability = np.full(len(test), development_prevalence)
baseline_summary = pd.DataFrame([
    {"参考项": "按开发期正样本比例给定常数概率", "概率值": development_prevalence,
     "测试Brier": brier_score_loss(test["Y"], constant_probability), "备注": "可实现的无特征概率基准"},
    {"参考项": "使用测试期实际正样本比例", "概率值": test["Y"].mean(),
     "测试Brier": brier_score_loss(test["Y"], np.full(len(test), test["Y"].mean())), "备注": "只是事后校准下界参考，不可用于真实预测"},
])
print("表11B：无特征概率基准与Brier参考")
display(baseline_summary)

quarter_metrics.to_csv(OUTPUT_DIR / "quarter_metrics.csv", index=False, encoding="utf-8-sig")
baseline_summary.to_csv(OUTPUT_DIR / "probability_baselines.csv", index=False, encoding="utf-8-sig")
"""
        ),
        code(
            """
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
for model_name, part in roc_points.groupby("model"):
    auc_value = model_metrics.set_index("模型").loc[model_name, "测试AUC"]
    axes[0].plot(part["fpr"], part["tpr"], linewidth=2, label=f"{model_name} (AUC={auc_value:.3f})")
axes[0].plot([0, 1], [0, 1], linestyle="--", color="#777777")
axes[0].set(title="图6：最终测试集ROC曲线", xlabel="假阳性率", ylabel="真阳性率")
axes[0].legend()

sns.barplot(data=model_metrics, x="模型", y="测试AUC", color="#C87500", ax=axes[1])
axes[1].axhline(0.5, color="#777777", linestyle="--")
axes[1].set(title="图7：四种模型测试AUC对比", xlabel="模型", ylabel="AUC", ylim=(0.45, max(0.7, model_metrics["测试AUC"].max() + 0.03)))
plt.tight_layout()
plt.savefig(CHART_DIR / "roc_and_model_comparison.png", bbox_inches="tight")
plt.show()

fig, axes = plt.subplots(2, 2, figsize=(10, 8))
for axis, (model_name, matrix) in zip(axes.ravel(), confusion_matrices.items()):
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Oranges", cbar=False, ax=axis)
    axis.set(title=model_name, xlabel="预测类别", ylabel="真实类别")
fig.suptitle("图8：四种模型混淆矩阵（阈值0.5）", y=1.01, fontsize=14)
plt.tight_layout()
plt.savefig(CHART_DIR / "confusion_matrices.png", bbox_inches="tight")
plt.show()
"""
        ),
        md("## 八、系数、特征重要性与概率信息"),
        code(
            """
importance_rows = []
for model_name, model_info in best_models.items():
    fitted = joblib.load(MODEL_DIR / f"{model_name}.joblib")
    inner_model = fitted.named_steps["model"]
    if model_name == "逻辑回归":
        values = inner_model.coef_[0]
        measure = "标准化系数"
    else:
        values = inner_model.feature_importances_
        measure = "模型重要性"
    for feature, value in zip(selected_features, values):
        importance_rows.append({"模型": model_name, "feature": feature, "特征": FEATURE_LABELS[feature], "指标": measure, "数值": value})

feature_importance = pd.DataFrame(importance_rows)
feature_importance.to_csv(OUTPUT_DIR / "feature_importance.csv", index=False, encoding="utf-8-sig")

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for axis, model_name in zip(axes, ["逻辑回归", "随机森林", "梯度提升"]):
    part = feature_importance.loc[feature_importance["模型"] == model_name].sort_values("数值")
    colors = ["#3B7A57" if value >= 0 else "#B74A3A" for value in part["数值"]]
    axis.barh(part["特征"], part["数值"], color=colors if model_name == "逻辑回归" else "#C87500")
    axis.set_title(model_name)
    axis.set_xlabel("标准化系数" if model_name == "逻辑回归" else "特征重要性")
fig.suptitle("图9：逻辑回归系数与树模型特征重要性", y=1.02, fontsize=14)
plt.tight_layout()
plt.savefig(CHART_DIR / "coefficients_and_importance.png", bbox_inches="tight")
plt.show()

print("表12：逻辑回归全部入选变量标准化系数")
display(feature_importance.loc[feature_importance["模型"] == "逻辑回归", ["特征", "数值"]].sort_values("数值", ascending=False))
"""
        ),
        code(
            """
# 技术面信息的增量价值：从同一组入选特征中移除两个历史价格特征，保持模型参数不变。
fundamental_only_features = [feature for feature in selected_features if feature not in TECHNICAL_FEATURES]
ablation_rows = []
for model_name, model_info in best_models.items():
    for feature_set_name, feature_set in [("混合X", selected_features), ("移除历史价格特征", fundamental_only_features)]:
        fold_aucs = []
        for train_dates, validation_dates in walk_forward_folds:
            train_fold = development.loc[development["Date"].isin(train_dates)]
            validation_fold = development.loc[development["Date"].isin(validation_dates)]
            estimator = clone(model_info["estimator"])
            estimator.fit(train_fold[feature_set], train_fold["Y"])
            fold_probability = estimator.predict_proba(validation_fold[feature_set])[:, 1]
            fold_aucs.append(roc_auc_score(validation_fold["Y"], fold_probability))
        estimator = clone(model_info["estimator"])
        estimator.fit(development[feature_set], development["Y"])
        probability = estimator.predict_proba(test[feature_set])[:, 1]
        ablation_rows.append({
            "模型": model_name, "特征集": feature_set_name, "特征数": len(feature_set),
            "滚动验证平均AUC": np.mean(fold_aucs), "测试AUC": roc_auc_score(test["Y"], probability),
        })
ablation_results = pd.DataFrame(ablation_rows)
print("表12A：历史价格特征增量信息检查")
display(ablation_results)
ablation_results.to_csv(OUTPUT_DIR / "technical_feature_ablation.csv", index=False, encoding="utf-8-sig")
"""
        ),
        code(
            """
# 概率是否具有补充信息：使用滚动验证AUC最高的模型，不根据测试AUC挑模型。
chosen_model_name = model_metrics.sort_values("滚动验证AUC", ascending=False).iloc[0]["模型"]
chosen_predictions = test_predictions.loc[test_predictions["model"] == chosen_model_name].copy()
chosen_predictions["概率组"] = chosen_predictions.groupby("Date")["probability"].transform(
    lambda values: pd.qcut(values.rank(method="first"), 5, labels=["Q1最低", "Q2", "Q3", "Q4", "Q5最高"])
)
probability_groups = chosen_predictions.groupby("概率组", observed=True, as_index=False).agg(
    样本数=("Code", "size"), 平均预测概率=("probability", "mean"), 实际正收益比例=("Y", "mean"),
    平均下季度收益=("Next_Ret", "mean"), 中位数下季度收益=("Next_Ret", "median")
)
print(f"表13：{chosen_model_name}预测概率的季度内五分组结果")
display(probability_groups)

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
sns.barplot(data=probability_groups, x="概率组", y="实际正收益比例", color="#C87500", ax=axes[0])
axes[0].set(title="图10：概率分组与实际上涨比例", xlabel="季度内预测概率五分组", ylabel="实际正收益比例")
sns.barplot(data=probability_groups, x="概率组", y="平均下季度收益", color="#3B7A57", ax=axes[1])
axes[1].axhline(0, color="#777777", linewidth=1)
axes[1].set(title="图11：概率分组与平均下季度收益", xlabel="季度内预测概率五分组", ylabel="平均收益率")
plt.tight_layout()
plt.savefig(CHART_DIR / "probability_group_analysis.png", bbox_inches="tight")
plt.show()

probability_groups.to_csv(OUTPUT_DIR / "probability_group_analysis.csv", index=False, encoding="utf-8-sig")
"""
        ),
        md(
            """
## 九、结果解读原则

1. AUC衡量模型对正负样本的排序能力，0.5约等于随机排序。不应只根据Accuracy判断模型，因为各季度正样本比例差异很大。
2. 逻辑回归系数表示条件预测方向，不是因果效应；树模型重要性也不表示经济因果性。
3. 上涨概率忽略收益幅度。它只有在测试期概率分组与实际上涨比例、实际收益呈稳定单调关系时，才适合在后续作为收益率预测的辅助置信度或风险过滤指标。
4. 数据只有10个原始季度，滞后后只有9个建模季度。因此数万条股票—季度记录不等于数万个独立市场环境，结论必须保持克制。
"""
        ),
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
