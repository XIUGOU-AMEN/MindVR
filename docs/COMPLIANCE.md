# 开源合规与数据声明

本文档说明本仓库在处理临床数据与模型权重时的边界，供参赛评审、开源使用者与后续维护者参考。

## 1. 数据红线

DAIC-WOZ（含 Extended DAIC-WOZ）由官方机构分发，使用协议的核心约束是：

- 仅限研究用途；
- **不得再分发**原始数据、转写文本、标签；
- 需在成果中正确引用原始论文。

因此本仓库**永久不包含**：

| 类别 | 示例 | 处理方式 |
| --- | --- | --- |
| 原始音视频 | `*.wav`、`*.mp4` | `.gitignore` 拦截 |
| 转写文本 | `*.transcript` | `.gitignore` 拦截 |
| 官方标签 | `full_split.csv`、`labels/`、`labels2019/` | `.gitignore` 拦截 |
| 个体级特征表 | `*merged*.csv` | `.gitignore` 拦截 |
| 预测产物 | `predictions.json` | `.gitignore` 拦截 |
| 模型缓存 | `model_cache/` | `.gitignore` 拦截 |

## 2. 合成数据

`data/demo/` 中的全部内容由 `scripts/generate_demo_data.py` 生成：

- 随机种子固定为 `20260101`；
- `participant_id` 为 `demo_xxxx`，与真实 ID 无对应关系；
- 文本来自固定模板，不含真实访谈片段；
- 特征由潜变量驱动的随机过程生成。

结论：合成数据可安全公开。

## 3. 模型权重

模型权重是否可公开，取决于训练数据的协议解释，存在争议。本项目的建议是：

### 推荐做法（默认）

- 仓库提交**合成数据训练的演示权重**；
- 真实数据训练的权重通过申请渠道单独提供；
- 在模型卡中注明用途限制。

### 若坚持提交真实数据训练的权重

必须做到：

1. 检查 joblib 内容，确认没有嵌入原始 `DataFrame`、文件路径、participant 列表：

   ```python
   import joblib
   obj = joblib.load("models/phq8_model.joblib")
   print(type(obj), obj.keys())
   ```

2. 在 `LICENSE` 与模型卡中声明"仅限学术研究、禁止商用、禁止用于临床决策"；
3. 不附带任何可用于反推个体的统计量（如每样本预测结果）。

## 4. 密钥与配置

- 所有密钥通过环境变量注入，`.env` 已被 `.gitignore` 忽略；
- 仓库只提交 `.env.example`，其中所有敏感字段为空或占位符；
- CI 不配置任何云端凭据，测试全部基于合成数据。

提交前自检：

```bash
git grep -nE "AK|SK|api_key|password|secret|token" -- ':!*.md'
```

## 5. 隐私与伦理

- 系统输出不构成医学诊断；
- 前端与文档均展示免责声明；
- 演示数据不来自真实个体；
- 若将来接入真实用户数据，需补充知情同意、数据最小化、访问审计与删除机制。

## 6. 提交前检查清单

- [ ] `git status` 中没有 `data/raw/`、`labels/`、`*.wav`、`predictions.json`
- [ ] `.env` 未被跟踪
- [ ] 模型文件不含个体级信息
- [ ] README 中的免责声明仍在
- [ ] `LICENSE` 中的模型权重 Notice 未被删除
- [ ] 截图与演示视频中没有真实 `participant_id`

推荐命令：

```bash
git ls-files
git status --ignored
git grep -nE "daic|DAIC|full_split|participant_[0-9]"
```