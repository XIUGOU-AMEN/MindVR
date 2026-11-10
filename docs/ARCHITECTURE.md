# 架构说明

## 1. 设计目标

1. **可演示**：评审打开网页 30 秒内能看到完整交互闭环。
2. **可复现**：没有 GPU、没有密钥、没有真实数据也能跑通。
3. **可解释**：每个分数都能说清"为什么"。
4. **可迁移**：本地模型与云端模型共用一套协议，切换只改环境变量。
5. **可合规开源**：真实数据与仓库物理隔离。

## 2. 分层

```text
接入层   FastAPI 路由（main.py）
应用层   分析编排（pipeline/orchestrator.py）
领域层   特征抽取 / 回归分类（pipeline/features.py, regress.py）
基础层   LLM 后端 / 转写 / 缓存 / 数据库（llm/, pipeline/transcribe.py, cache.py, db.py）
```

依赖方向自上而下，领域层不感知 Web 框架，便于单独测试与复用。

## 3. 关键设计取舍

### 3.1 为什么不让大模型直接输出 PHQ-8 分数

PHQ-8 是 0–24 的序数变量。让语言模型直接回归会退化为"输出安全中间值"
（大量样本集中在 7–10），MAE 高、相关系数低、且无法解释。

本项目采用两段式：

```text
LLM  →  症状线索强度（0–3，可解释）
监督模型  →  PHQ-8 分数 + 概率
```

LLM 的价值在于理解自由文本中的隐晦表达，而不是做数值回归。

### 3.2 为什么模型后端要做成可插拔

比赛要求"基于华为云产品"，开源要求"任何人 clone 即可运行"，两者对基础设施的要求相反。
抽象出 `LLMBackend` 后：

| 场景 | `LLM_BACKEND` | 依赖 |
| --- | --- | --- |
| 比赛演示 / 线上部署 | `maas` | 华为云 MaaS |
| 开源复现 / 离线开发 | `local` | 本地 vLLM / Ollama |
| 无模型环境 | 未配置 | 规则词典，功能降级但不崩溃 |

### 3.3 为什么用 WebXR 而不是 Unity

Web Demo 与 VR 若分两套技术栈，需要同时维护 `React + Unity` 两条链路，
联调成本高、部署链路长、开源复现门槛高。

WebXR 方案的优势：

- 一套 `React` 代码同时覆盖网页与沉浸模式；
- 浏览器直接打开，无需安装客户端；
- 可部署为普通静态资源，与后端共用 Nginx；
- 演示视频录制成本低。

### 3.4 为什么归因用线性系数而不是 SHAP

`shap` 会引入较重的依赖与运行时开销。由于分类头是逻辑回归，
标准化特征 × 系数本身就是一致、可加、可解释的线性归因，
足够支撑"主要依据"展示。若后续换成树模型，可再引入 SHAP。

## 4. 请求时序

```text
Client
  → POST /api/v1/analyze (transcript)
    → extract_text_features()            规则词典，毫秒级
    → llm_cue_features()                 可选，失败静默回落到规则结果
    → merge_features()                   补齐声学/视觉默认值
    → DepressionModel.predict()
        → regressor.predict()            PHQ-8 分数
        → classifier.predict_proba()     抑郁概率
        → _attribute()                   Top-K 归因
    → persist()                          写入 RDS/SQLite
  ← AnalysisResult
```

## 5. 扩展点

| 想扩展什么 | 改哪里 |
| --- | --- |
| 接入声学特征（openSMILE） | 生成 JSON 后走 `load_precomputed()` |
| 接入视觉特征（OpenFace） | 同上，`visual_path` |
| 换模型 | 替换 `backend/pipeline/regress.py` |
| 换大模型 | 新增 `LLMBackend` 子类并在 `factory.py` 注册 |
| 换数据库 | 修改 `DATABASE_URL` |
| 增加异步任务 | 在 `orchestrator` 外包一层队列（Redis + RQ/Celery） |

## 6. 性能与资源

- 演示数据 240 条，训练 < 5 秒（CPU）
- 单次推理 < 50 ms（不含 LLM 网络往返）
- 后端常驻内存约 200 MB（含 sklearn 与 pandas）
- 前端产物 < 1 MB（gzip 后）

## 7. 已知限制

1. 声学/视觉特征默认为群体中位数，真实多模态能力依赖外部特征提取器。
2. 华为云 SIS 短语音接口对时长有限制，长访谈需切片。
3. 归因是线性近似，不代表因果。
4. 模型在合成数据上训练，指标仅用于验证工程链路，不代表真实临床性能。