# 从零到上线执行手册（RUNBOOK）

> 面向「华为云码道 CodeArts 大赛 · 赛题1」的完整操作步骤。
> 每一步都给出：**做什么 → 命令 → 如何验证 → 要截什么图**。
> 时间基准：2026-11-09 起，2026-12-01 前交付。

---

## 0. 一页速览

今天必须开始的 5 件事：

| # | 事项 | 是否可代办 | 预计耗时 |
| --- | --- | --- | --- |
| 1 | 比赛报名 + 华为云实名认证 + 代金券申请 | 否（需本人账号） | 30 分钟 |
| 2 | 安装 Node.js LTS（前端当前无法构建） | 可协助 | 10 分钟 |
| 3 | 本地跑通后端（合成数据即可） | 已就绪 | 5 分钟 |
| 4 | 开通 MaaS，跑通一次云端模型调用 | 否（需控制台操作） | 20 分钟 |
| 5 | 建立 CodeArts 使用留痕文件夹 | 可协助 | 5 分钟 |

**验收铁节点：11/22 前必须有一个公网可打开、能出结果的页面。**

---

## 1. 账号与资质（本人操作，无法代办）

### 1.1 比赛报名

在赛题页面完成报名，记下参赛队伍名称与队长账号。

### 1.2 华为云账号

1. 注册华为云账号并完成**实名认证**（个人认证即可，未认证无法购买 RDS/Redis/ECS）。
2. 进入「费用中心」确认账户可正常下单。
3. 按组委会通知提交**代金券申请**。申请通过前不要提前购买大规格实例。

### 1.3 AI 开发者空间

按赛题提供的入口开通 AI 开发者空间账号，用于云端开发环境与部署演示。

### 1.4 CodeArts 代码智能体

确认你使用的是**华为云码道 CodeArts 代码智能体**（不是其他同名 IDE）。
本项目所有代码均可在此智能体中生成与修改。

### 1.5 开源平台

准备 Gitee 或 GitHub 账号（入围总决赛后必须开源）。

---

## 2. 软件下载清单

### 2.1 必需

| 软件 | 用途 | 当前状态 | 安装方式 |
| --- | --- | --- | --- |
| Git | 版本管理与上传 | 已有 2.55 | 无需安装 |
| Python 3.10+ | 后端运行 | 已有 3.10.10（`py`） | 无需安装 |
| **Node.js LTS** | 前端构建、WebXR | **缺失** | `winget install OpenJS.NodeJS.LTS` |
| CodeArts 代码智能体 | 比赛必选开发工具 | 使用中 | 赛题入口下载 |

### 2.2 可选

| 软件 | 用途 | 说明 |
| --- | --- | --- |
| Docker Desktop | 本地容器验证 | Windows 家庭版需 WSL2；不装也能直接 `uvicorn` 运行 |
| 浏览器（Chrome/Edge） | WebXR 演示 | 建议 Chrome，支持 WebXR 模拟 |

### 2.3 安装后统一验证

```bash
py scripts/check_env.py
py scripts/check_env.py --cloud
```

要求：**「阻塞」数量为 0**。`[warn]` 项在对应阶段再处理。

---

## 3. 本地跑通（约 30 分钟）

### 3.1 安装后端依赖

```bash
py -m pip install -r requirements.txt -r requirements-dev.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> 国内网络必须使用镜像源，否则大概率超时。

### 3.2 生成合成数据并训练

```bash
py scripts/generate_demo_data.py
py scripts/train.py --no-cv
```

预期：

```text
已生成 240 条合成样本
模型已保存 -> .../models/phq8_model.joblib
```

### 3.3 启动后端并自检

```bash
py -m uvicorn backend.main:app --reload --port 8000
```

另开终端：

```bash
py scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

预期：

```text
[ok] health status=ok model_loaded=True
[ok] demo score=12.7 risk=moderate evidence=6
[ok] analyze score=11.24 risk=moderate backend=local
smoke test passed
```

### 3.4 构建并启动前端

```bash
cd frontend
npm install
npm run build
npm run dev
```

打开 <http://localhost:5173>，验收三点：

1. 点击「运行示例」能看到分数、风险等级、Top-6 依据；
2. 点击「进入沉浸式场景」能看到三维咨询室，氛围随风险变化；
3. 点击「进入 VR 模式」不报错（无头显时浏览器会提示不支持，属正常）。

> 前端构建失败时把完整报错贴出来，优先看 `tsc` 的类型错误。

### 3.5 本地验收清单

- [ ] `pytest` 12 个用例通过
- [ ] `ruff check backend scripts tests` 无错误
- [ ] 三个接口冒烟通过
- [ ] 前端三条交互全部可用
- [ ] 切换 `LLM_BACKEND=local/maas` 不报错

---

## 4. 华为云资源开通

> 赛题要求「基于已有智能体和 Skills，进行关联 RDS、REDIS 等华为云服务的快速开通创建」。
> **优先用 CodeArts 的 Skill 完成开通，并截图 Skill 执行过程**，这本身就是评分点。

### 4.1 开通顺序

按依赖关系从轻到重：

```text
OBS（存储） → MaaS（模型） → Redis（缓存） → RDS MySQL（数据） → ECS（部署）
```

### 4.2 MaaS（最先跑通，决定演示效果）

1. 控制台搜索「ModelArts Studio」，进入模型服务；
2. 开通 Qwen 系列模型（以控制台可用列表为准）；
3. 获取 **OpenAI 兼容** 的调用地址与 API Key；
4. 写入 `.env`：

   ```bash
   LLM_BACKEND=maas
   MAAS_BASE_URL=<控制台提供的兼容地址>
   MAAS_MODEL=<模型名>
   MAAS_API_KEY=<API Key>
   ```

5. 验证（重启后端后执行）：

   ```bash
   py scripts/smoke_test.py --base-url http://127.0.0.1:8000
   ```

   `analyze` 行应显示 `backend=maas`。

**截图点**：模型服务开通页、调用地址与模型名页面、`backend=maas` 的冒烟输出。

### 4.3 OBS

1. 控制台搜索「对象存储服务 OBS」→ 创建桶；
2. 区域与 ECS 保持一致，访问策略设为私有，建议开启服务端加密；
3. 安装 SDK：`py -m pip install -r requirements-cloud.txt`；
4. `.env`：`OBS_BUCKET=<桶名>`、`USE_CLOUD_STORAGE=true`。

**截图点**：桶列表页（桶名可见，不要露出 AK/SK）。

### 4.4 Redis

1. 控制台搜索「分布式缓存服务 DCS」→ 创建 Redis（最小规格即可）；
2. 记录内网地址与密码；
3. `.env`：`REDIS_URL=redis://:<password>@<host>:6379/0`；
4. 验证：重复分析同一文本，第二次响应应更快。

**截图点**：实例详情页、`REDIS_URL` 生效后的分析响应。

### 4.5 RDS MySQL

1. 控制台搜索「云数据库 RDS」→ 购买 MySQL（最小规格）；
2. VPC 与 ECS 相同，安全组只放行内网；
3. 创建库 `mindvr` 与业务账号；
4. 安装驱动：

   ```bash
   py -m pip install pymysql
   ```

5. `.env`：

   ```bash
   DATABASE_URL=mysql+pymysql://<user>:<password>@<host>:3306/mindvr?charset=utf8mb4
   ```

6. 验证：启动后端后，在 RDS 中应能看到 `analysis_records` 表，且每次分析新增一行。

**截图点**：实例详情、表结构、数据行。

### 4.6 ECS

1. 购买 ECS（2 核 4G 起），与 RDS/Redis 同 VPC；
2. 安全组放行 `22`、`8080`；仅调试期放行 `8000`；
3. 安装 Docker（按官方文档执行），或直接使用 Python 运行。

**截图点**：实例详情、安全组规则。

---

## 5. 部署上线

### 方式 A：ECS + Docker（推荐，演示稳定）

```bash
ssh <user>@<ecs-ip>
git clone <你的仓库地址> mindvr
cd mindvr
cp .env.example .env
vi .env
docker compose up --build -d
docker compose ps
```

公网验证：

```bash
py scripts/smoke_test.py --base-url http://<公网IP>:8000
```

浏览器打开 `http://<公网IP>:8080`。

### 方式 B：CodeArts auto-deploy Skill

1. 在 CodeArts 中加载 auto-deploy Skill；
2. 指向仓库根目录，选择 `docker-compose.yml`；
3. 环境变量通过密钥管理注入，不要写进文件；
4. 部署完成后执行冒烟测试并截图。

**截图点**：Skill 执行日志、部署成功页、公网访问截图、冒烟通过输出。

---

## 6. 留痕材料清单（评分核心）

赛题明确要求体现「需求理解 → 代码生成 → 项目构建 → 问题修复 → 部署上线」五环节。
建议在仓库外建一个 `deliverables/` 文件夹（**不要提交到 Git**），按下面命名存档：

| 编号 | 文件 | 内容 |
| --- | --- | --- |
| 01 | `01-需求理解.png` | CodeArts 中描述需求的对话 |
| 02 | `02-代码生成.png` | 生成 `backend/main.py`、`frontend/src/App.tsx` 的记录 |
| 03 | `03-项目构建.png` | `npm run build`、`pytest` 通过 |
| 04 | `04-问题修复.png` | 一次真实报错的定位与修复（推荐用 participant_id 类型不一致问题） |
| 05 | `05-Skills开通.png` | Redis/RDS 通过 Skill 开通的过程 |
| 06 | `06-部署上线.png` | 部署日志 + 公网页面 |
| 07 | `07-数据合规.png` | `.gitignore` 拦截真实数据的说明 |

> 截图中的密钥、AK/SK、数据库密码、真实 participant_id 必须打码。

---

## 7. 演示脚本（3 分钟）

1. 打开公网页面，指出右上角「模型已加载 / LLM 后端 maas」；
2. 点「运行示例」→ 展示 12.7 分、中度风险、6 条依据；
3. 粘贴一段更严重的文本 → 分数上升、依据变化；
4. 点「进入沉浸式场景」→ 三维咨询室随风险变色，呼吸球引导；
5. 点「进入 VR 模式」→ 展示 WebXR；
6. 口播：「同一份代码，改一个环境变量就从本地模型切到华为云 MaaS」。

---

## 8. 开源交付

```bash
git init
git add .
git commit -m "feat: MindVR multimodal depression perception demo with WebXR"
git branch -M main
git remote add origin <仓库地址>
git push -u origin main
```

推送前自检：

```bash
git status --short
git grep -nE "daic|DAIC|full_split|participant_[0-9]|AK|SK|api_key"
```

要求包含：源代码、依赖环境、部署指导、使用文档、许可证、Demo 截图或视频链接。
本仓库已全部具备，对应文件：

- `README.md`、`docs/RUNBOOK.md`、`docs/ARCHITECTURE.md`、`docs/HUAWEICLOUD_DEPLOY.md`
- `docs/COMPLIANCE.md`、`LICENSE`
- `requirements.txt`、`requirements-cloud.txt`、`docker-compose.yml`

---

## 9. 时间线

| 日期 | 目标 | 验收 |
| --- | --- | --- |
| 11/09–11/12 | 环境补齐、MaaS 跑通、留痕目录建立 | `backend=maas` 冒烟通过 |
| 11/13–11/15 | Redis + RDS 开通并接入 | 表中有数据、缓存生效 |
| 11/16–11/18 | ECS 部署 + 公网访问 | 公网 URL 可打开 |
| 11/19–11/22 | 前端联调与 VR 打磨 | 三条交互全通，录屏 |
| 11/23–11/26 | 材料补齐、截图归档 | 7 份留痕齐全 |
| 11/27–11/30 | 开源、视频、最终自检 | 仓库可 clone 即跑 |

---

## 10. 费用与资源释放

- RDS、Redis、ECS、OBS 均为按量或包周期计费，**演示结束后及时释放或停机**；
- 代金券有使用范围与有效期，以组委会通知为准；
- 每日检查「费用中心」，避免欠费导致公网 Demo 失效；
- 提交前至少保留 3 天在线，供评审访问。

---

## 11. 故障排查

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `ModuleNotFoundError` | 依赖未装或解释器不对 | 用 `py -m pip install ...`，确认 `py -V` |
| pip 超时 | 默认源慢 | 加 `-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| `模型文件不存在` | 未训练 | `py scripts/train.py --no-cv` |
| `analyze` 返回 503 | 模型未加载 | 同上 |
| `backend=null` | MaaS 地址或 Key 未配置 | 检查 `.env` 与 `LLM_BACKEND` |
| 前端 `npm install` 失败 | Node 未装或网络 | 装 Node LTS，使用 `npm config set registry https://registry.npmmirror.com` |
| 浏览器无 VR 按钮响应 | 设备不支持 WebXR | 属正常，3D 场景仍可用 |
| RDS 连不上 | 安全组/VPC 不一致 | 放行内网、确认同 VPC |

---

## 附：当前仓库已完成状态（2026-11-09）

- 后端链路实测通过：合成数据 → 训练 → 预测 → 评估
- 单元测试 12/12 通过，`ruff` 无错误
- `health` / `demo` / `analyze` 三接口冒烟通过
- 前端代码完成，**因本机无 Node 尚未构建验证**（第 3.4 步补齐）
- 华为云资源尚未开通（第 4 章）