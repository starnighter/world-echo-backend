# Progress

## 当前已完成模块

- 项目骨架与基础设施
- 配置层、统一响应/异常、JWT 基础能力
- 异步 SQLAlchemy ORM 与数据库初始化
- 路由骨架与核心 schema/service 初版
- 认证模块
- 文件上传模块
- 歌曲、歌单、广场、点赞模块
- ASR HTTP 接口与 WebSocket 桥接
- 三类 SSE 生成接口与 Mock 外部服务
- Essentia 模型文件已复制到 `app/models/`
- README、本地运行配置、Dockerfile、docker-compose、测试基座
- 依赖安装与本地虚拟环境验证
- Docker Compose 冒烟验证
- mock OAuth 登录与 `/auth/me` 鉴权链路验证
- API、SSE、WebSocket ASR 自动化测试
- 真实第三方适配代码补齐（QQ OAuth、SiliconFlow、MiniMax、讯飞 RTASR、Essentia）
- 可用真实第三方链路验证与运行期修正
  - SiliconFlow 图像理解链路验证通过
  - `prompt_refiner_service.py` 已切换到 `audio_to_music_prompt.py` 的提示词模板，并完成真实调用验证
  - MiniMax 流式适配已修正，真实 SSE 可收到最终 `status=2`
  - 讯飞实时 WebSocket 桥接已修正关闭路径，不再因上游提前关闭导致后端 `500`

## 当前正在做的模块

- 真实联调阶段已完成当前可验证部分，剩余未做的是缺少凭证或缺少配置的链路：GitHub/QQ OAuth、文件转写 ASR、全真实 voice 生成。

## 修改过的文件列表

- `BACKEND_PLAN.md`
- `PROGRESS.md`
- `.env.example`
- `app/core/config.py`
- `app/api/v1/generation.py`
- `app/services/asr_service.py`
- `app/services/music_generation_service.py`
- `app/services/prompt_refiner_service.py`

## 已运行的测试和结果

- `python3 -m compileall app`：通过。
- `.venv/bin/pytest app/tests -q`：`14 passed in 7.33s`。
- 直接调用 `VisionPromptService.analyze_image()`（真实 SiliconFlow + `Qwen/Qwen3-VL-32B-Instruct`）：通过，返回 `scene/objects/mood/style_prompt`。
- 直接调用 `PromptRefinerService.refine_from_audio_features()`（真实 SiliconFlow，新模板）：通过，返回中文提示词、英文提示词和参数建议。
- 直接调用 `MusicGenerationService.stream_generate()`（真实 MiniMax）：通过，收到多段 `status=1`，最终收到 `status=2`，返回完整音频与 `extra_info`。
- 真实 `POST /v1/songs/generate/image` SSE：通过，逐行消费时收到多段 `status=1`，最终收到 `status=2` 和完整 `song`。
- 真实 `WS /v1/asr/stream`：通过握手并收到 `started` 事件；发送静音字节后上游返回 `engine error|37005:Client idle timeout`，后端已正确透传错误且未再抛 `500`。

## 尚未解决的问题

- `cover_url` 当前用本地生成占位文件表示，后续可替换为真实封面生成逻辑。
- 当前 `.env` 中仍未填写 `GITHUB_CLIENT_ID/SECRET` 与 `QQ_CLIENT_ID/SECRET`，因此未做真实 OAuth 联调。
- `ASR_API_URL` 仍为空，因此 `/v1/asr/transcribe` 与 `/v1/songs/generate/voice` 里的“文件转写”仍不会走真实服务。
- `MOCK_AUDIO_ANALYSIS=true` 且 `ENABLE_ESSENTIA=false` 时，voice 生成仍不是完整真实链路。
- 讯飞 RTASR 对静音/无效音频帧会返回 `engine error|37005:Client idle timeout`；当前证明的是桥接和错误透传正常，不是“有效语音样本识别通过”。
- 某些非流式 HTTP 客户端（如直接 `httpx.post()` 等整个 SSE body 读完）可能在最终事件已返回后看到 `incomplete chunked read`；前端按 SSE 逐行消费不受影响，但仍建议补一个收尾回归测试。
- 目前覆盖的是主 happy path；更细的异常路径、并发场景、SSE 断线恢复仍可继续补强。
- `docs/wolrd-echo-architecture.png` 文件名与需求描述不一致，实施按仓库实际文件名处理。

## 下一次继续时应该执行的具体任务

- 补齐 GitHub/QQ OAuth 凭证并做真实回调联调。
- 提供一个可被文件转写链路使用的真实 `ASR_API_URL`，验证 `/v1/asr/transcribe` 和 `/v1/songs/generate/voice`。
- 关闭 `MOCK_AUDIO_ANALYSIS`、开启 `ENABLE_ESSENTIA=true`，用真实音频样本验证完整 voice 生成链路。
- 为 MiniMax 真实流格式、XFYun 错误透传和 SSE 最终收尾增加回归测试。
- 增加失败路径、权限错误、重复提交、封禁用户、SSE 失败事件的自动化测试。
- 增加并发点赞、歌单排序边界、文件大小/格式校验的回归测试。
