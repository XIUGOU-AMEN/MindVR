# 华为云部署与赛题材料清单

本文档面向参赛交付，说明如何在华为云上完成「资源开通 → 部署 → 演示 → 留痕」。

## 1. 赛题要求对照

| 要求 | 本项目动作 | 留痕材料 |
| --- | --- | --- |
| 使用华为云码道 CodeArts 代码智能体 | 用 CodeArts 生成、修复、构建本项目 | 对话截图、生成记录 |
| 关联 RDS、Redis 等云服务快速开通 | 按第 2 节顺序开通 | 控制台截图、连接验证输出 |
| 应用在华为云快速部署 | 第 4 节部署流程 | 部署日志、公网访问链接 |
| 可视化 Demo 展示核心功能 | 前端上传 → 结果 → VR | Demo 截图、录屏 |
| 体现全链路开发价值 | 需求 → 生成 → 构建 → 修复 → 部署 | 每个环节各 1 张截图 |

官方资源入口（来自赛题说明页）：

- CodeArts 代码智能体下载及使用指导：<https://developer.huaweicloud.com/codeartsco.html?source=dmzntcompetition>
- 智能体实践案例中心：<https://aidevbp.developer.huaweicloud.com/>
- Skills 一键部署示例：<https://gitcode.com/weixin_43883336/auto-deploy/blob/main/auto-deploy-case-study.md>
- AI 开发者空间：<https://devstation.developer.huaweicloud.com/aidevspace>

> 具体 endpoint、区域与资费以控制台实际分配为准，本文档不写死任何地址。

## 2. 云资源开通顺序

建议按「先存储、再计算、最后数据库」的顺序，避免依赖等待。

### 2.1 OBS 对象存储

1. 控制台 → 对象存储服务 OBS → 创建桶；
2. 区域选择与后续 ECS 相同的区域，降低内网延迟；
3. 建议开启服务端加密，访问策略设为私有；
4. 记录桶名，填入 `.env` 的 `OBS_BUCKET`；
5. 开启 `USE_CLOUD_STORAGE=true` 前，先确认已安装 `requirements-cloud.txt`。

### 2.2 MaaS（ModelArts Studio）

1. 控制台 → ModelArts Studio → 模型服务；
2. 开通 Qwen 系列模型服务，获取 **OpenAI 兼容** 的调用地址与 API Key；
3. 填入：

   ```bash
   LLM_BACKEND=maas
   MAAS_BASE_URL=<控制台提供的兼容地址>
   MAAS_MODEL=<模型名>
   MAAS_API_KEY=<API Key>
   ```

4. 验证：

   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/analyze \
     -F "transcript=最近一直失眠，什么都不想做，很累"
   ```

   响应中的 `llm_backend` 应为 `maas`。

### 2.3 SIS 语音交互服务

1. 控制台 → 语音交互服务 SIS → 开通；
2. 创建 AK/SK，填入 `.env` 的 `HUAWEI_AK` / `HUAWEI_SK` / `HUAWEI_PROJECT_ID`；
3. 安装 SDK：`pip install -r requirements-cloud.txt`；
4. 设置 `USE_CLOUD_ASR=true`；
5. 注意短语音接口的时长限制，长访谈需切片后逐段识别。

### 2.4 RDS for MySQL

1. 控制台 → 云数据库 RDS → 购买 MySQL 实例；
2. 与 ECS 放在同一 VPC，安全组仅放行内网；
3. 创建数据库 `mindvr` 与业务账号；
4. 安装驱动并配置连接串：

   ```bash
   pip install pymysql
   ```

   ```bash
   DATABASE_URL=mysql+pymysql://<user>:<password>@<host>:3306/mindvr?charset=utf8mb4
   ```

5. 启动服务后表会自动创建（`init_db()`）。

### 2.5 Redis

1. 控制台 → 分布式缓存服务 DCS → 创建 Redis；
2. 记录内网地址，填入 `REDIS_URL=redis://:<password>@<host>:6379/0`；
3. 未配置时系统自动降级为进程内缓存，不影响演示。

## 3. CodeArts 智能体使用留痕

建议按以下顺序截图，覆盖赛题要求的五个环节：

| 环节 | 截图内容 |
| --- | --- |
| 需求理解 | 在 CodeArts 中描述"多模态抑郁感知 + WebXR Demo"的需求 |
| 代码生成 | 生成 `backend/main.py`、`frontend/src/App.tsx` 的记录 |
| 项目构建 | `npm run build`、`pytest` 通过的结果 |
| 问题修复 | 一次真实报错的定位与修复过程（例如 ID 类型不匹配） |
| 部署上线 | auto-deploy Skill 执行日志与公网访问成功页面 |

## 4. 部署方式

### 方式 A：docker compose（推荐）

在华为云 ECS 上：

```bash
git clone <your-repo-url> mindvr
cd mindvr
cp .env.example .env
vi .env                 # 填入 RDS / Redis / MaaS 配置
docker compose up --build -d
docker compose ps
```

开放安全组端口 `8080`（前端）与 `8000`（后端，可选）。

部署完成后执行冒烟测试，一条命令覆盖健康检查、示例分析与文本分析：

```bash
python scripts/smoke_test.py --base-url http://<公网IP>:8000
```

预期输出：

```text
[ok] health status=ok model_loaded=True
[ok] demo score=12.7 risk=moderate evidence=6
[ok] analyze score=11.24 risk=moderate backend=maas
smoke test passed
```

### 方式 B：CodeArts auto-deploy Skill

1. 在 CodeArts 中加载 auto-deploy Skill；
2. 指向仓库根目录，选择 `docker-compose.yml`；
3. 填写环境变量（敏感项用密钥管理，不写进配置文件）；
4. 执行部署，检查健康检查接口：

   ```bash
   curl http://<公网IP>:8000/api/v1/health
   curl http://<公网IP>:8080/
   python scripts/smoke_test.py --base-url http://<公网IP>:8000
   ```

## 5. 演示脚本（建议 3 分钟）

1. 打开网页，展示健康状态与模型状态；
2. 点击「运行示例」，展示分数、风险等级、Top-K 依据；
3. 粘贴一段更严重的访谈文本，展示分数上升与依据变化；
4. 点击「进入沉浸式场景」，展示三维咨询室与氛围随风险变化；
5. 打开「进入 VR 模式」，展示 WebXR 能力；
6. 切到 MaaS 配置，说明"同一份代码，切换一个环境变量即可跑在华为云上"。

## 6. 交付清单

- [ ] 公网可访问的 Demo 链接
- [ ] 开源仓库（Gitee / GitHub）
- [ ] README + 部署指导 + 许可证
- [ ] 架构图与数据流图
- [ ] 云资源开通截图（OBS / MaaS / SIS / RDS / Redis）
- [ ] CodeArts 全流程截图
- [ ] Demo 录屏（3 分钟内）
- [ ] 数据合规声明（`docs/COMPLIANCE.md`）