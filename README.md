# MindVR · 多模态心理状态感知与沉浸式交互

> 一个可复现、可部署、可开源的多模态抑郁风险感知演示系统。
> 访谈文本 + 声学/视觉特征 → PHQ-8 分数估计与可解释依据 → Web Demo / WebXR 沉浸式场景。

> ⚠️ 本项目是**学术研究与技术演示作品**，不是医疗器械，**不能用于临床诊断**，也不能替代专业心理评估。

---

## 目录

- [执行手册（从零到上线，推荐先读）](docs/RUNBOOK.md)
- [1. 项目定位](#1-项目定位)
- [2. 系统架构](#2-系统架构)
- [3. 目录结构](#3-目录结构)
- [4. 快速开始](#4-快速开始)
- [5. 配置说明](#5-配置说明)
- [6. 命令速查](#6-命令速查)
- [7. HTTP API](#7-HTTP API)
- [8. 华为云接入](#8-华为云接入)
- [9. Docker 部署](#9-Docker 部署)
- [10. 开源合规与数据声明](#10-开源合规与数据声明)
- [11. 常见问题](#11-常见问题)
- [12. 许可证](#12-许可证)

---

## 1. 项目定位

本项目解决两个工程问题：

1. **如何让大模型真正参与抑郁风险感知，而不是让它直接“猜分数”。**
   大模型只负责从访谈文本中抽取症状线索（睡眠、兴趣、精力、自我价值、注意力、食欲、动作迟缓），
   最终 PHQ-8 分数由轻量监督模型给出，避免大模型回归常见的“分数坍缩”。

2. **如何把算法封装成可演示、可部署、可沉浸交互的产品。**
   后端提供标准化 API，前端提供网页 Demo 与 WebXR 场景，可部署到华为云并一键开源。

核心特性：

- **可插拔模型后端**：本地 vLLM/Ollama 与华为云 MaaS 共用 OpenAI 兼容协议，一个环境变量切换。
- **离线可跑**：没有 GPU、没有 API Key、没有任何真实数据，也能用合成数据跑通全流程。
- **可解释输出**：每个预测附带 Top-K 特征归因，直接驱动前端可视化与 VR 氛围。
- **合规开源**：仓库不含任何 DAIC-WOZ 原始数据、标签或可反推个体的中间产物。

---

## 2. 系统架构

```mermaid
flowchart TB
    subgraph Client["客户端"]
        W["Web Demo<br/>React + Vite"]
        V["WebXR 沉浸场景<br/>react-three-fiber"]
    end

    subgraph Backend["FastAPI 后端"]
        API["/api/v1/analyze"]
        ORC["分析编排"]
        FEAT["特征抽取<br/>规则词典 + LLM 补强"]
        MODEL["PHQ-8 回归 / 分类<br/>sklearn"]
    end

    subgraph HuaweiCloud["华为云"]
        MAAS["MaaS · Qwen"]
        SIS["SIS 语音识别"]
        OBS["OBS 对象存储"]
        RDS["RDS MySQL"]
        REDIS["Redis 缓存"]
    end

    W --> API
    V --> API
    API --> ORC
    ORC --> FEAT
    FEAT --> MAAS
    API --> SIS
    API --> OBS
    ORC --> MODEL
    API --> RDS
    API --> REDIS
```

数据流：

```
访谈音频/文本
  → （可选）华为云 SIS 转写
  → 规则词典抽取文本线索
  → （可选）MaaS · Qwen 补强症状线索
  → 融合声学/视觉特征
  → sklearn 回归 + 分类
  → PHQ-8 分数 / 风险概率 / Top-K 归因
  → Web 可视化 + WebXR 氛围渲染
```

---

## 3. 目录结构

```text
.
├── backend/                  后端服务
│   ├── main.py               FastAPI 入口与路由
│   ├── config.py             环境变量配置
│   ├── schemas.py            请求/响应数据契约
│   ├── cache.py              Redis / 内存缓存
│   ├── db.py                 SQLAlchemy 数据层
│   ├── llm/                  可插拔大模型后端
│   └── pipeline/             特征抽取、回归、编排、转写
├── frontend/                 React + WebXR 前端
├── scripts/                  数据生成、训练、预测、评测
├── tests/                    单元测试
├── docs/                     架构、合规、华为云部署文档
├── data/demo/                合成演示数据（可安全开源）
├── models/                   训练产物（joblib）
├── Dockerfile                后端镜像
├── docker-compose.yml        一键编排
└── .env.example              配置模板（不含任何密钥）
```

---

## 4. 快速开始

> 需要分阶段操作步骤、华为云开通顺序与留痕清单，请先读 [`docs/RUNBOOK.md`](docs/RUNBOOK.md)。
> 环境是否就绪，一条命令即可确认：`py scripts/check_env.py --cloud`

### 5.1 环境要求

- Python 3.10+
- Node.js 18+（仅前端需要）
- 无需 GPU，无需联网，无需真实数据集

### 5.2 后端：3 条命令跑通

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

# 1) 生成合成演示数据
python scripts/generate_demo_data.py

# 2) 训练演示模型
python scripts/train.py

# 3) 启动服务
uvicorn backend.main:app --reload --port 8000
```

验证（推荐，一条命令覆盖三个接口）：

```bash
python scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

预期输出：

```text
[ok] health status=ok model_loaded=True
[ok] demo score=12.7 risk=moderate evidence=6
[ok] analyze score=11.24 risk=moderate backend=local
smoke test passed
```

也可以手动验证：

```bash
curl http://127.0.0.1:8000/api/v1/health
curl -X POST http://127.0.0.1:8000/api/v1/demo
```

交互式文档：<http://127.0.0.1:8000/docs>

### 5.3 前端

```bash
cd frontend
npm install
npm run dev
```

打开 <http://localhost:5173>，点击「运行示例」即可看到完整结果，
再点击「进入沉浸式场景」体验 WebXR 三维咨询室。

### 5.4 一键 Docker

```bash
cp .env.example .env
docker compose up --build
```

- 前端：<http://localhost:8080>
- 后端：<http://localhost:8000/docs>

> 镜像构建阶段会自动生成合成数据并训练演示模型，因此首次构建稍慢。

---

## 5. 配置说明

复制模板后按需修改：

```bash
cp .env.example .env
```

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `LLM_BACKEND` | `local` 或 `maas` | `local` |
| `LOCAL_BASE_URL` | 本地 vLLM/Ollama 的 OpenAI 兼容地址 | `http://127.0.0.1:8001/v1` |
| `LOCAL_MODEL` | 本地模型名 | `qwen2.5-7b-instruct` |
| `MAAS_BASE_URL` | 华为云 MaaS endpoint（以控制台分配为准） | 空 |
| `MAAS_MODEL` | MaaS 上的模型名 | 空 |
| `MAAS_API_KEY` | MaaS 凭据 | 空 |
| `DATABASE_URL` | 数据库连接串，线上填 RDS MySQL | `sqlite:///./data/app.db` |
| `REDIS_URL` | Redis 连接串，为空时自动降级为内存缓存 | 空 |
| `USE_CLOUD_ASR` | 是否启用华为云 SIS 转写 | `false` |
| `MODEL_PATH` | 模型文件路径 | `models/phq8_model.joblib` |
| `PHQ8_BINARY_THRESHOLD` | 抑郁二分类阈值 | `10` |

**安全约束**：`.env` 已被 `.gitignore` 忽略。任何情况下都不要把密钥写进代码或提交到仓库。

### 6.1 切换到华为云 MaaS

```bash
LLM_BACKEND=maas
MAAS_BASE_URL=<从华为云控制台获取的 OpenAI 兼容地址>
MAAS_MODEL=<控制台上可用的 Qwen 模型名>
MAAS_API_KEY=<你的 API Key>
```

未配置凭据时，系统会自动回落到 `null` 后端，特征抽取只用规则词典，
**不会报错**，保证离线可用。

---

## 6. 命令速查

| 目的 | 命令 |
| --- | --- |
| 生成合成数据 | `python scripts/generate_demo_data.py` |
| 训练模型 | `python scripts/train.py` |
| 训练并跳过交叉验证 | `python scripts/train.py --no-cv` |
| 批量预测 | `python scripts/predict.py --data data/demo/features_demo.csv --out predictions.json` |
| 评估预测 | `python scripts/evaluate.py --predictions predictions.json --labels data/demo/features_demo.csv` |
| 部署冒烟测试 | `python scripts/smoke_test.py --spawn` |
| 运行测试 | `python -m pytest -q` |
| 代码检查 | `ruff check backend scripts tests` |
| 前端构建 | `cd frontend && npm run build` |

`predictions.json` 采用以下结构，字段名与常见官方评测脚本保持一致：

```json
[
  {
    "participant_id": "demo_0001",
    "prediction": {
      "phq8_score_estimation": 7.42,
      "depression_probability": 0.31,
      "depression_classification": 0,
      "risk_level": "mild"
    }
  }
]
```

---

## 7. HTTP API

### `GET /api/v1/health`

```json
{ "status": "ok", "version": "0.1.0", "llm_backend": "local", "model_loaded": true }
```

### `GET /api/v1/model/info`

返回特征列表、模型版本与二分类阈值。

### `POST /api/v1/analyze`

`multipart/form-data`：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `transcript` | text | 二选一 | 访谈转写文本 |
| `audio` | file | 二选一 | 音频文件（需开启 `USE_CLOUD_ASR`）或 DAIC 转写 CSV/TSV，后端自动解析 |
| `participant_id` | text | 否 | 默认 `anonymous` |

> 上传 `*_Transcript.csv` 时，后端会过滤咨询师发言、按时间排序并拼接为文本；
> 上传音频则依赖华为云 SIS 转写，需先设置 `USE_CLOUD_ASR=true` 并安装 `requirements-cloud.txt`。

响应：

```json
{
  "participant_id": "anonymous",
  "phq8_score_estimation": 12.36,
  "depression_probability": 0.74,
  "depression_classification": 1,
  "risk_level": "moderate",
  "evidence": [
    {
      "feature": "sleep_mention",
      "label_zh": "睡眠问题提及",
      "value": 0.66,
      "contribution": 0.42,
      "direction": "up"
    }
  ],
  "transcript_excerpt": "最近一直睡不好……",
  "model_version": "phq8-gbdt-v1",
  "llm_backend": "local",
  "latency_ms": 18
}
```

### `POST /api/v1/demo`

无需任何输入，返回内置示例文本的分析结果，用于快速验收部署。

---

## 8. 华为云接入

完整步骤见 [`docs/HUAWEICLOUD_DEPLOY.md`](docs/HUAWEICLOUD_DEPLOY.md)。要点：

1. **MaaS**：开通 ModelArts Studio，获取 OpenAI 兼容地址与 API Key，填入 `.env`。
2. **OBS**：创建桶，用于存放上传的访谈音频；生产环境建议开启服务端加密。
3. **SIS**：开通语音交互服务，设置 `USE_CLOUD_ASR=true`，并安装 `requirements-cloud.txt`。
   长音频会自动按 55 秒切片，详见 [`docs/ASR.md`](docs/ASR.md)。
4. **RDS MySQL**：创建实例后将 `DATABASE_URL` 指向它，例如
   `mysql+pymysql://user:password@host:3306/mindvr`（额外安装 `pymysql`）。
5. **Redis**：创建实例后填入 `REDIS_URL`。
6. **部署**：使用 CodeArts auto-deploy Skill，或直接 `docker compose up -d`。

### 9.1 计费与密钥归属

本项目**不内置任何凭据**，也不会代替使用者调用他人账号。

| 服务 | 计费方式 | 由谁承担 |
| --- | --- | --- |
| MaaS 大模型 | 按 token（输入/输出分别计价） | 使用者自己的华为云账号 |
| SIS 语音转写 | 按音频时长 | 使用者自己的华为云账号 |
| RDS / Redis / OBS / ECS | 按规格与用量 | 使用者自己的华为云账号 |

开源使用者有三种运行方式，按成本从低到高：

1. `LLM_BACKEND=null`：只用规则词典，零成本、可完全离线；
2. `LLM_BACKEND=local`：本地 vLLM / Ollama，只有电费；
3. `LLM_BACKEND=maas`：使用自己的华为云 Key，费用由自己的账号结算。

**默认支持范围**：纯文本与 DAIC 逐句转写 CSV。
音频（`.wav`）需要先开启华为云 SIS 转写，长访谈还需按 60 秒切片；未开启时前端会直接提示改选 `_Transcript.csv`，不会提交无效请求。

---

## 9. Docker 部署

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

停止与清理：

```bash
docker compose down
```

后端镜像在构建时会自动执行「生成合成数据 → 训练模型」，因此开箱即用。

---

## 10. 开源合规与数据声明

### 11.1 仓库**不包含**什么

- ❌ DAIC-WOZ 原始音视频、转写文本、官方标签
- ❌ 任何含真实 `participant_id` 的中间表、预测文件、特征文件
- ❌ 模型缓存、虚拟环境、离线安装包
- ❌ 任何 API Key、AK/SK、数据库密码

`.gitignore` 已对上述内容做强制拦截。`data/demo/` 下的数据由
`scripts/generate_demo_data.py` 用固定随机种子**完全合成**，与任何真实受试者无关。

### 11.2 仓库**包含**什么

- ✅ 全部源代码、测试、部署配置
- ✅ 合成演示数据与训练脚本
- ✅ 可选：基于公开基准训练的模型权重（`models/*.joblib`）

若提交模型权重，请在模型卡中注明训练数据来源与使用限制。
本项目的 `LICENSE` 仅在代码部分适用 MIT；**模型权重仅限学术研究使用**。

### 11.3 数据集获取

DAIC-WOZ 需通过官方渠道申请并签署使用协议，**不得再分发**。
本项目不提供任何数据下载链接或镜像。详见 [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md)。

---

## 11. 常见问题

**Q：没有 GPU 能跑吗？**
能。演示链路使用 sklearn，CPU 秒级完成；大模型是可选增强项。

**Q：没有华为云账号能跑吗？**
能。`LLM_BACKEND=local` 或干脆不配置，系统会回落到规则词典模式，全流程仍可运行。

**Q：为什么不用大模型直接输出 PHQ-8 分数？**
大模型直接回归分数会向均值坍缩，MAE 难以接受。本项目的做法是「LLM 抽线索 + 监督模型给分」，
可解释性和量化指标都更可控。

**Q：VR 需要专门的头显吗？**
不需要。浏览器打开即可获得 3D 场景；接入 WebXR 设备（或手机 Cardboard）后可沉浸式体验。

**Q：为什么评估脚本要做那么多校验？**
因为 `participant_id` 类型不一致（`int` vs `str`）会让样本悄悄匹配为 0，指标全部变成 NaN 却不报错。
`scripts/evaluate.py` 已统一为字符串比较并显式报错。

---

## 12. 许可证

代码采用 [MIT License](LICENSE)。
模型权重与数据集使用受额外条款约束，见 `LICENSE` 末尾的 Notice 与
[`docs/COMPLIANCE.md`](docs/COMPLIANCE.md)。