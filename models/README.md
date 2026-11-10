# models/ 目录说明

## 文件

| 文件 | 说明 | 是否提交 |
| --- | --- | --- |
| `phq8_model.joblib` | 训练好的回归 + 分类流水线 | 可选（需附模型说明） |
| `*.tmp` | 训练中间产物 | 否 |

## 为什么用单个 joblib 而不是 `.pth` + `.pkl`

旧方案把模型权重和标准化器拆成两个文件，容易出现版本错配、路径失效、加载顺序错误。
本项目将 `StandardScaler + GradientBoostingRegressor` 与 `StandardScaler + LogisticRegression`
封装在同一个 joblib 中，一次加载即可推理，便于开源复现。

## 模型结构

- 回归头：`StandardScaler → GradientBoostingRegressor(n_estimators=200, max_depth=3)`
- 分类头：`StandardScaler → LogisticRegression(class_weight="balanced")`
- 输出：PHQ-8 分数（裁剪到 `[0, 24]`）+ 抑郁概率 + 二分类标签
- 归因：标准化特征 × 线性分类器系数，取绝对值 Top-6

## 训练与复现

```bash
python scripts/generate_demo_data.py
python scripts/train.py
```

或使用自己的特征表（需包含 `participant_id`、`phq8_score`、`phq8_binary`
以及 `backend/pipeline/features.py` 中定义的全部特征列）：

```bash
python scripts/train.py --data /path/to/features.csv --out models/phq8_model.joblib
```

## 提交权重的注意事项

如果你打算把基于真实数据训练的权重提交到公开仓库：

1. 确认数据集协议允许分发衍生模型（DAIC-WOZ 对再分发有严格限制，存在争议）；
2. 在模型卡中写明训练数据来源、用途限制、已知偏差；
3. **不要**在 joblib 中嵌入原始 DataFrame、文件路径、participant 列表；
4. 明确声明权重仅供学术研究，不用于临床或商业用途。

更稳妥的做法是：仓库只提交在合成数据上训练的演示权重，
真实数据权重通过申请渠道单独分发。