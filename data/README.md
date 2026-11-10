# data/ 目录说明

## 目录约定

```text
data/
├── demo/                     合成演示数据（可提交到 Git）
│   ├── features_demo.csv     240 条完全合成的多模态特征
│   └── transcripts_demo.jsonl 与特征一一对应的合成访谈文本
├── raw/                      真实原始数据（禁止提交，已在 .gitignore 中）
├── private/                  私有中间结果（禁止提交）
├── interim/                  特征提取中间产物（禁止提交）
└── processed/                可用于训练的特征表（禁止提交）
```

## demo 数据的性质

`data/demo/` 下的所有内容由 `scripts/generate_demo_data.py` 生成：

- 使用固定随机种子 `20260101`，可完全复现；
- `participant_id` 全部是 `demo_0001` ~ `demo_0240`；
- 特征由潜变量随机过程生成，与任何真实受试者无关；
- 文本来自三个固定模板，不含任何真实访谈内容。

因此 demo 数据**可以安全地提交到公开仓库**。

重新生成：

```bash
python scripts/generate_demo_data.py
```

## 真实数据

本仓库**不提供、不托管、不镜像** DAIC-WOZ 或任何临床数据。
如需复现论文级实验，请自行通过官方渠道申请，并严格遵守其使用协议。

真实数据请放在 `data/raw/`，该目录已被 `.gitignore` 忽略。
提交前请执行以下自检：

```bash
git status --ignored
git ls-files | Select-String -Pattern "daic|labels|transcript|\.wav|\.mp4"
```

### DAIC 转写文件

DAIC-WOZ 每个受访者目录下的 `*_Transcript.csv` 是**逐句转写表**（时间、文本、置信度），
不是一段连续文本。批量转换为纯文本：

```bash
python scripts/extract_daic_transcripts.py --root "E:/Create/daic_woz_data" --out data/raw/transcripts.csv
```

也可以在前端直接上传单个 `*_Transcript.csv`，后端会自动过滤咨询师发言、按时间排序并拼接。
原始音频 `*_AUDIO.wav` 需要先经服务端 ASR（华为云 SIS 或本地 Whisper）转成文本，模型不直接读取音频。

## 特征列说明

| 分组 | 特征 |
| --- | --- |
| 文本语义 | `neg_sentiment_ratio`、`first_person_ratio`、`self_negation_ratio`、`word_count`、`avg_sentence_len` |
| 症状线索 | `sleep_mention`、`anhedonia_mention`、`fatigue_mention`、`worthlessness_mention`、`concentration_mention`、`appetite_mention`、`psychomotor_mention` |
| 声学 | `f0_mean`、`f0_std`、`energy_mean`、`speech_rate`、`pause_ratio`、`jitter`、`shimmer` |
| 视觉 | `au_intensity_mean`、`au_intensity_std`、`gaze_away_ratio`、`smile_freq`、`head_motion` |

真实场景下，声学特征建议用 openSMILE（eGeMAPS 子集）提取，
视觉特征建议用 OpenFace 提取 AU 强度与头部姿态，再以 JSON 形式传入
`backend.pipeline.features.load_precomputed()`。