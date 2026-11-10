# 音频转写（ASR）接入说明

本文档说明如何把「上传音频 → 文本 → 抑郁风险分析」这条链路接起来。

## 1. 链路设计

```text
上传 wav
  → 校验采样率（仅支持 8k / 16k）
  → 按 55 秒切片（标准库 wave，无需 ffmpeg）
  → 逐段调用华为云 SIS 短语音识别
  → 拼接文本
  → 进入文本分析流水线
```

切片是必须的：SIS 短语音接口对单段音频有时长限制（通常 60 秒），而 DAIC 访谈通常十几到几十分钟。

## 2. 开通华为云 SIS

1. 登录华为云控制台，搜索 **语音交互服务 SIS**；
2. 在「西南-贵阳一」（与 MaaS、RDS、Redis 同区）开通服务；
3. 创建访问密钥 **AK / SK**；
4. 在「我的凭证」里复制 **项目 ID（Project ID）**；
5. 确认该服务在代金券覆盖范围内。

## 3. 配置 `.env`

```bash
USE_CLOUD_ASR=true
HUAWEI_AK=<你的 AK>
HUAWEI_SK=<你的 SK>
HUAWEI_PROJECT_ID=<项目 ID>
HUAWEI_REGION=cn-southwest-2

# 可选：切片长度与识别属性
SIS_ASR_MAX_SECONDS=55
SIS_ASR_PROPERTY=chinese_16k_general
```

安装 SDK（仅云端模式需要）：

```bash
E:\PythonEnvs\python310\python.exe -m pip install -r requirements-cloud.txt
```

## 4. 本地验证

先只检查切片，不消耗额度：

```bash
E:\PythonEnvs\python310\python.exe scripts\check_asr.py --file "E:/Create/daic_woz_data/300_P/300_AUDIO.wav"
```

输出会显示：

- 采样率、声道、位深、时长；
- 会切成几段；
- 是否支持 SIS；
- `USE_CLOUD_ASR` 当前值。

真实调用：

```bash
E:\PythonEnvs\python310\python.exe scripts\check_asr.py --file "E:/Create/daic_woz_data/300_P/300_AUDIO.wav" --call
```

## 5. HTTP 接口

### `POST /api/v1/transcribe`

只做转写，返回文本与分段信息，便于调试：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/transcribe ^
  -F "audio=@E:/Create/daic_woz_data/300_P/300_AUDIO.wav"
```

响应：

```json
{
  "transcript": "……",
  "characters": 322,
  "backend": "huawei-sis",
  "chunks": 12,
  "failed_chunks": 0
}
```

### `POST /api/v1/analyze`

上传同一个文件，会先转写再做分析：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze ^
  -F "audio=@E:/Create/daic_woz_data/300_P/300_AUDIO.wav" ^
  -F "participant_id=300"
```

## 6. 音频格式要求

| 项目 | 要求 |
|---|---|
| 容器 | wav（PCM） |
| 采样率 | 8000 或 16000 Hz |
| 声道 | 单声道最佳 |
| 编码 | PCM 16-bit |

不满足时，接口会返回明确错误并给出转换命令：

```bash
ffmpeg -i input.wav -ar 16000 -ac 1 output.wav
```

## 7. 计费

- SIS 按**音频时长**计费，不是 token；
- 后续 MaaS 线索抽取按 token 计费；
- 两者都使用**使用者自己的华为云账号**；
- 本项目不内置任何密钥。

## 8. 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `未安装华为云 SIS SDK` | 未装云端依赖 | `pip install -r requirements-cloud.txt` |
| `缺少华为云凭据` | AK/SK/ProjectId 为空 | 检查 `.env` |
| `采样率仅支持 8000/16000` | wav 采样率不符 | 用 ffmpeg 转换 |
| `无法解析 wav 文件` | 上传的是 mp3/m4a | 先转 wav |
| `转写结果为空` | 静音、格式错误、额度不足 | 换一段音频重试，查看控制台 |
| 分段失败数 > 0 | 单段识别失败 | 脚本会自动重试一次并跳过该段 |
| 长音频很慢 | 逐段串行调用 | 正常；可按需调整 `SIS_ASR_MAX_SECONDS` |

## 9. 演示口径

默认演示仍使用 DAIC-WOZ 自带 `_Transcript.csv`，保证可复现、零额度消耗。

音频链路属于「已实现、开通即可用」的扩展能力，答辩时可以说明：

> 音频链路已实现为华为云 SIS 转写（含 55 秒自动切片）；演示使用数据集自带高质量转写以保证稳定复现，接入 SIS 后无需改代码即可切换到音频输入。