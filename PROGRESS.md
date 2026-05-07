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
- 普通账号注册/登录接口
- API 文档与 OpenAPI JSON 同步更新（包含 `WS /v1/asr/stream`）
- 基于 `test-files/` 的三条音乐生成接口回放验证
- 生成音乐统一收集到本地播放目录 `playback-check/20260507-203716/`
- `music-cover` 公网音频 URL 翻唱验证
- 本地 Python 3.11 虚拟环境重建，并安装 `essentia-tensorflow` 与全部项目依赖
- `test-files/test-environmental-sound.m4a` 的本地 Essentia 真分析验证
- 真实 `POST /v1/songs/generate/voice` 链路验证（Essentia -> SiliconFlow -> MiniMax，`model_used=music-2.6`）
- 真实 Essentia 音频生成结果已复制到 `playback-check/20260507-203716/voice-essentia-real.mp3`
- 本地仅保留 Python 3.11 的 `.venv`，已删除旧的 `.venv-py314-backup`
- 已定位 PyCharm 对 `essentia.standard` 的引用报错来源，并修正 `.idea/misc.xml` 中残留的 `Python 3.14` Black SDK 配置
- 歌曲生成完成后的 `cover_url` 值已改为随机 `1-8` 的字符串，字段名保持不变

## 当前正在做的模块

- 当前阶段已收口，剩余未完成的是缺少凭证或缺少配置的链路：GitHub/QQ OAuth、文件转写 ASR。

## 修改过的文件列表

- `BACKEND_PLAN.md`
- `PROGRESS.md`
- `docs/API-DOCS.md`
- `docs/world-echo-api.json`
- `database/init.sql`
- `.env.example`
- `app/api/v1/auth.py`
- `app/core/config.py`
- `app/core/security.py`
- `app/api/v1/generation.py`
- `app/db/init_db.py`
- `app/db/models.py`
- `app/services/asr_service.py`
- `app/services/audio_analysis_service.py`
- `app/schemas/auth.py`
- `app/services/auth_service.py`
- `app/services/music_generation_service.py`
- `app/services/prompt_refiner_service.py`
- `app/services/storage_service.py`
- `Dockerfile`
- `docker-compose.yml`
- `.idea/misc.xml`
- `app/tests/test_api_endpoints.py`
- `playback-check/20260507-203716/prompt.mp3`
- `playback-check/20260507-203716/image.mp3`
- `playback-check/20260507-203716/public-url-music-cover.mp3`
- `playback-check/20260507-203716/voice.mp3`
- `playback-check/20260507-203716/voice-essentia-real.mp3`
- `playback-check/20260507-203716/summary.json`

## 已运行的测试和结果

- `python3 -m compileall app`：通过。
- `.venv/bin/pytest app/tests -q`：`14 passed in 7.33s`。
- 直接调用 `VisionPromptService.analyze_image()`（真实 SiliconFlow + `Qwen/Qwen3-VL-32B-Instruct`）：通过，返回 `scene/objects/mood/style_prompt`。
- 直接调用 `PromptRefinerService.refine_from_audio_features()`（真实 SiliconFlow，新模板）：通过，返回中文提示词、英文提示词和参数建议。
- 直接调用 `MusicGenerationService.stream_generate()`（真实 MiniMax）：通过，收到多段 `status=1`，最终收到 `status=2`，返回完整音频与 `extra_info`。
- 真实 `POST /v1/songs/generate/image` SSE：通过，逐行消费时收到多段 `status=1`，最终收到 `status=2` 和完整 `song`。
- 真实 `WS /v1/asr/stream`：通过握手并收到 `started` 事件；发送静音字节后上游返回 `engine error|37005:Client idle timeout`，后端已正确透传错误且未再抛 `500`。
- `.venv/bin/pytest app/tests -q`（新增普通注册/登录后再次执行）：`14 passed in 69.11s`。
- `python3 -m compileall app`（新增远程 `source_url` 物化支持后再次执行）：通过。
- 使用普通注册账号跑三条生成接口（未调用直接 ASR 接口）：
  - `POST /v1/songs/generate/prompt`：通过，`status=2`
  - `POST /v1/songs/generate/image`：通过，`status=2`
  - `POST /v1/songs/generate/voice`：通过，`status=2`
- 三个生成结果已复制到 `playback-check/20260507-203716/`，可直接播放检查。
- 使用公网参考音频 URL 跑 `POST /v1/songs/generate/voice`，参数 `model_used=music-cover`：通过，`status=2`，结果已复制到 `playback-check/20260507-203716/public-url-music-cover.mp3`。
- `PYENV_VERSION=3.11.9 pyenv exec python -m venv .venv`：通过，本地虚拟环境已切到 Python 3.11.9。
- `.venv/bin/python -m pip install --no-build-isolation -e '.[dev,essentia]'`：通过，`essentia-tensorflow` 与开发依赖已安装。
- `.venv/bin/python -c "import essentia, matplotlib, numpy, fastapi; print('ok')"`：通过。
- `MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python ... AudioAnalysisService.analyze(test-files/test-environmental-sound.m4a)`：通过，返回 `bpm=119.87`、`key=F minor`、真实 `genre/tags` 与 `spectrogram_path`。
- 本地 Python 3.11 进程启动真实模式 API：通过，服务运行在 `http://127.0.0.1:8006`。
- 使用普通注册账号调用真实 `POST /v1/songs/generate/voice`（`test-files/test-environmental-sound.m4a`，`ENABLE_ESSENTIA=true`，`MOCK_AUDIO_ANALYSIS=false`，`MOCK_VISION_PROMPT=false`，`MOCK_MINIMAX=false`，`MOCK_ASR=true`，`model_used=music-2.6`）：通过，收到多段 `status=1`，最终收到 `status=2`，生成歌曲 `3c1fd869-d017-436e-8e3b-5e8feb5eb8bf`，结果文件 `/static/generated/music/2026/05/07/1cb8440987dcd88d98996e506e6c0ff9.mp3`，并已复制到 `playback-check/20260507-203716/voice-essentia-real.mp3`。
- `.venv/bin/python` 运行时检查 `essentia.standard.FrameGenerator / Spectrum / Windowing / MonoLoader / RhythmExtractor2013 / KeyExtractor / TensorflowPredict2D / TensorflowPredictEffnetDiscogs`：全部存在，说明不是代码引用错误。
- 检查 `.venv/lib/python3.11/site-packages/essentia/standard.py`：这些类由 `_reloadAlgorithms()` 和 `create_python_algorithms()` 在模块导入时动态注入，属于运行时生成，不是静态声明。
- 检查 PyCharm 配置：`.idea/misc.xml` 中 `ProjectRootManager` 已是 `Python 3.11`，但 `Black` 组件仍残留 `Python 3.14 (world-echo-backend)`，已修正为 `Python 3.11 (world-echo-backend)`。
- 已更新 SSE 生成测试，校验 `cover_url` 字段值在 `1-8` 范围内。

## 尚未解决的问题

- `cover_url` 当前用本地生成占位文件表示，后续可替换为真实封面生成逻辑。
- 当前 `.env` 中仍未填写 `GITHUB_CLIENT_ID/SECRET` 与 `QQ_CLIENT_ID/SECRET`，因此未做真实 OAuth 联调。
- `ASR_API_URL` 仍为空，因此 `/v1/asr/transcribe` 与 `/v1/songs/generate/voice` 里的“文件转写”仍不会走真实服务。
- 基于 `test-files/test-environmental-sound.m4a` 的本地 `voice` 生成验证为了避免外部模型拉取本机 `localhost` 音频失败，显式使用了 `model_used=music-2.6`，没有走 `music-cover` 的远端参考音频拉取模式。
- 现已补上对公网音频 URL 的支持，并用 iTunes 公开预览地址实际跑通 `music-cover`。
- 讯飞 RTASR 对静音/无效音频帧会返回 `engine error|37005:Client idle timeout`；当前证明的是桥接和错误透传正常，不是“有效语音样本识别通过”。
- 某些非流式 HTTP 客户端（如直接 `httpx.post()` 等整个 SSE body 读完）可能在最终事件已返回后看到 `incomplete chunked read`；前端按 SSE 逐行消费不受影响，但仍建议补一个收尾回归测试。
- 中断或非流式消费 SSE 时，数据库里可能留下 `status=processing` 的历史记录（例如 `164bc139-f743-4a2a-a09f-a7dd99e5321a`）；需要后续补客户端断连收尾策略。
- PyCharm 对 `essentia.standard` 的 “Cannot find reference ...” 仍大概率会继续出现，因为这是 IDE 对动态注入 API 的静态分析局限，不是当前代码本身错误；3.14 配置残留已消除，但不能保证完全消除这类黄线。
- 目前覆盖的是主 happy path；更细的异常路径、并发场景、SSE 断线恢复仍可继续补强。
- `docs/wolrd-echo-architecture.png` 文件名与需求描述不一致，实施按仓库实际文件名处理。

## 下一次继续时应该执行的具体任务

- 补齐 GitHub/QQ OAuth 凭证并做真实回调联调。
- 提供一个可被文件转写链路使用的真实 `ASR_API_URL`，验证 `/v1/asr/transcribe` 和 `/v1/songs/generate/voice`。
- 为 MiniMax 真实流格式、XFYun 错误透传和 SSE 最终收尾增加回归测试。
- 为中断/非流式消费 SSE 的场景补任务收尾测试和状态恢复策略。
- 增加失败路径、权限错误、重复提交、封禁用户、SSE 失败事件的自动化测试。
- 增加并发点赞、歌单排序边界、文件大小/格式校验的回归测试。
