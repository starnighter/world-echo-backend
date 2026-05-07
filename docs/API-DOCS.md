# World Echo API 接口文档

## 通用约定

| 项目 | 说明 |
|------|------|
| Base URL | `https://api.world-echo.com/v1` |
| 认证方式 | Bearer Token（JWT），放在 `Authorization` 请求头 |
| Content-Type | `application/json`（文件上传用 `multipart/form-data`） |
| 时间格式 | ISO 8601 UTC，如 `2026-05-01T12:00:00Z` |
| 分页参数 | `?page=1&page_size=20`，page 从 1 开始 |

### 统一响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### 通用错误码

| code | 说明 |
|------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未登录 / Token 无效 |
| 403 | 无权限（如操作他人资源） |
| 404 | 资源不存在 |
| 409 | 冲突（如重复点赞） |
| 422 | 业务校验失败（如封禁用户） |
| 429 | 请求频率限制 |
| 500 | 服务器内部错误 |

---

## 1. 认证模块 (Auth)

### 1.1 注册

使用用户名/邮箱/密码注册普通账号。注册成功后直接返回 JWT 和用户信息。

```
POST /auth/register
```

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名，2-50 字符 |
| email | string | 否 | 邮箱，若填写需唯一 |
| password | string | 是 | 密码，6-128 字符 |

**请求示例**

```json
{
  "username": "music_lover",
  "email": "user@example.com",
  "password": "secret123"
}
```

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "username": "music_lover",
      "email": "user@example.com",
      "avatar_url": null,
      "is_banned": false,
      "created_at": "2026-05-01T12:00:00Z",
      "oauths": []
    }
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 409 | 用户名或邮箱已存在 |

---

### 1.2 登录

使用用户名或邮箱 + 密码登录普通账号。

```
POST /auth/login
```

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| account | string | 是 | 用户名或邮箱 |
| password | string | 是 | 密码 |

**请求示例**

```json
{
  "account": "music_lover",
  "password": "secret123"
}
```

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "username": "music_lover",
      "email": "user@example.com",
      "avatar_url": null,
      "is_banned": false,
      "created_at": "2026-05-01T12:00:00Z",
      "oauths": []
    }
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 401 | 账号或密码错误 |
| 422 | 用户已被封禁 |

---

### 1.3 获取第三方登录 URL

获取指定 OAuth 提供商的授权跳转地址。

```
GET /auth/oauth/{provider}/url
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| provider | string | 是 | 提供商标识：`github`、`qq` |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "url": "https://github.com/login/oauth/authorize?client_id=xxx&redirect_uri=xxx&scope=user"
  }
}
```

---

### 1.4 第三方登录回调

用户完成第三方授权后的回调接口，自动注册新用户或登录已有用户。前端拿到授权码后调用此接口。

```
GET /auth/oauth/{provider}/callback
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| provider | string | 是 | 提供商标识：`github`、`qq` |

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | 是 | OAuth 授权码 |
| state | string | 否 | 防 CSRF 状态码 |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "username": "music_lover",
      "email": "user@example.com",
      "avatar_url": "https://cdn.world-echo.com/avatars/xxx.jpg",
      "is_banned": false,
      "created_at": "2026-05-01T12:00:00Z"
    },
    "is_new_user": true
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 400 | 授权码无效或已过期 |
| 422 | 用户已被封禁 |

---

### 1.5 登出

```
POST /auth/logout
```

**请求头**

| Header | 值 |
|--------|---|
| Authorization | Bearer {token} |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

---

### 1.6 获取当前用户信息

```
GET /auth/me
```

**请求头**

| Header | 值 |
|--------|---|
| Authorization | Bearer {token} |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "username": "music_lover",
    "email": "user@example.com",
    "avatar_url": "https://cdn.world-echo.com/avatars/xxx.jpg",
    "is_banned": false,
    "oauths": [
      { "provider": "github", "created_at": "2026-05-01T12:00:00Z" }
    ]
  }
}
```

---

### 1.7 更新用户资料

```
PUT /auth/me
```

**请求头**

| Header | 值 |
|--------|---|
| Authorization | Bearer {token} |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 否 | 新用户名，2-50 字符 |
| email | string | 否 | 新邮箱 |
| avatar_url | string | 否 | 新头像 URL（先通过上传接口获取） |

**请求示例**

```json
{
  "username": "new_name",
  "avatar_url": "https://cdn.world-echo.com/avatars/new.jpg"
}
```

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "username": "new_name",
    "email": "user@example.com",
    "avatar_url": "https://cdn.world-echo.com/avatars/new.jpg",
    "is_banned": false
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 409 | 用户名已被占用 |

---

## 2. 文件上传模块 (Upload)

### 2.1 上传图片

上传图片文件，返回 CDN 地址。支持 jpg、png、webp，单文件最大 10MB。

```
POST /upload/image
```

**请求头**

| Header | 值 |
|--------|---|
| Authorization | Bearer {token} |
| Content-Type | multipart/form-data |

**请求体（form-data）**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 图片文件 |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "url": "https://cdn.world-echo.com/uploads/images/2026/05/01/abc123.jpg"
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 400 | 文件格式不支持或文件过大 |

---

### 2.2 上传音频

上传音频文件，返回 CDN 地址。支持 mp3、wav、m4a、ogg，单文件最大 50MB。

```
POST /upload/audio
```

**请求头**

| Header | 值 |
|--------|---|
| Authorization | Bearer {token} |
| Content-Type | multipart/form-data |

**请求体（form-data）**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 音频文件 |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "url": "https://cdn.world-echo.com/uploads/audio/2026/05/01/def456.wav"
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 400 | 文件格式不支持或文件过大 |

---

## 3. AI 生成模块 (Generation)

> 生成接口采用 **SSE（Server-Sent Events）** 流式返回，参考 MiniMax music-2.6 的 `stream: true` 模式。
> 前端通过 `EventSource` 或 `fetch + ReadableStream` 接收实时生成进度和音频数据。

### SSE 通用说明

**请求头**

| Header | 值 |
|--------|---|
| Authorization | Bearer {token} |
| Accept | text/event-stream |
| Content-Type | application/json |

**SSE 事件格式**

每个 `data` 行为一个 JSON 对象，结构如下：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": 1,
    "audio_hex": "...",
    "extra_info": null,
    "song": null
  }
}
```

**`data.status` 枚举值**

| status | 说明 | 含义 |
|--------|------|------|
| 1 | 合成中 | `audio_hex` 为当前片段的 hex 编码音频数据，前端可拼接播放 |
| 2 | 生成完成 | `audio_hex` 为最后一段音频数据，`extra_info` 包含完整元数据，`song` 包含歌曲完整信息 |
| 3 | 生成失败 | `message` 中包含错误描述 |

**`extra_info` 字段（仅 status=2 时返回）**

| 字段 | 类型 | 说明 |
|------|------|------|
| duration | number | 音频总时长（毫秒） |
| sample_rate | integer | 采样率（如 44100） |
| channel | integer | 声道数 |
| bitrate | integer | 比特率 |
| size | integer | 音频总大小（字节） |

**`song` 字段（仅 status=2 时返回）**

包含歌曲在数据库中的完整记录（同歌曲详情接口返回结构）。

---

### 3.1 图片生成歌曲（SSE）

通过图片生成歌曲，以 SSE 流式返回生成进度和音频数据。

```
POST /songs/generate/image
```

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| source_url | string | 是 | 图片 URL（通过上传接口获取） |
| prompt | string | 否 | 额外的风格/内容提示词 |
| lyrics | string | 否 | 自定义歌词，为空则 AI 生成 |
| is_instrumental | boolean | 否 | 是否纯音乐，默认 false |
| model_used | string | 否 | 模型选择，默认 `music-2.6`，可选 `music-cover` |

**请求示例**

```json
{
  "source_url": "https://cdn.world-echo.com/uploads/images/2026/05/01/abc123.jpg",
  "prompt": "温暖的民谣风格",
  "is_instrumental": false,
  "model_used": "music-2.6"
}
```

**SSE 事件流示例**

```
data: {"code":0,"message":"success","data":{"status":1,"audio_hex":"49443304...","extra_info":null,"song":null}}

data: {"code":0,"message":"success","data":{"status":1,"audio_hex":"fffb9244...","extra_info":null,"song":null}}

data: {"code":0,"message":"success","data":{"status":1,"audio_hex":"fffb92c6...","extra_info":null,"song":null}}

data: {"code":0,"message":"success","data":{"status":2,"audio_hex":"fffb9044...","extra_info":{"duration":25364,"sample_rate":44100,"channel":2,"bitrate":256000,"size":813651},"song":{"id":"b2c3d4e5-f6a7-8901-bcde-f12345678901","title":"夏日海风","cover_url":"https://cdn.world-echo.com/covers/xxx.jpg","music_url":"https://cdn.world-echo.com/music/xxx.mp3","source_type":"image","status":"done","prompt":"温暖的民谣风格","lyrics":"蓝天白云下...","is_instrumental":false,"model_used":"music-2.6","source_url":"https://cdn.world-echo.com/uploads/images/abc123.jpg","is_public":false,"published_at":null,"likes_count":0,"created_at":"2026-05-01T12:00:00Z","updated_at":"2026-05-01T12:02:30Z"}}}
```

**前端处理建议**

```javascript
const response = await fetch('/v1/songs/generate/image', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Accept': 'text/event-stream',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ source_url, prompt })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  const lines = text.split('\n').filter(line => line.startsWith('data: '));

  for (const line of lines) {
    const json = JSON.parse(line.slice(6));
    const { status, audio_hex, extra_info, song } = json.data;

    if (status === 1) {
      // 合成中：拼接 audio_hex 片段用于实时预览
      appendAudioChunk(audio_hex);
    } else if (status === 2) {
      // 完成：song 包含完整歌曲信息，music_url 可用于持久播放
      onGenerationComplete(song, extra_info);
    } else if (status === 3) {
      // 失败
      onGenerationError(json.message);
    }
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 400 | 请求参数错误 |
| 401 | 未登录 |
| 422 | 业务校验失败（如用户被封禁） |

---

### 3.2 声音生成歌曲（SSE）

通过声音生成歌曲，以 SSE 流式返回。

```
POST /songs/generate/voice
```

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| source_url | string | 是 | 音频 URL（通过上传接口获取） |
| prompt | string | 否 | 额外的风格/内容提示词 |
| lyrics | string | 否 | 自定义歌词，为空则由模型自动生成 |
| is_instrumental | boolean | 否 | 是否纯音乐，默认 false |
| model_used | string | 否 | 模型选择，默认 `music-cover` |

**请求示例**

```json
{
  "source_url": "https://cdn.world-echo.com/uploads/audio/2026/05/01/def456.wav",
  "prompt": "电子流行风格",
  "model_used": "music-cover"
}
```

**SSE 事件流**

同 3.1，`song.source_type` 为 `voice`，`song.source_url` 为上传的音频地址。

---

### 3.3 提示词生成歌曲（SSE）

通过纯文字提示词生成歌曲，以 SSE 流式返回。

```
POST /songs/generate/prompt
```

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| prompt | string | 是 | 音乐风格/内容描述 |
| lyrics | string | 否 | 自定义歌词 |
| is_instrumental | boolean | 否 | 是否纯音乐，默认 false |
| model_used | string | 否 | 模型选择，默认 `music-2.6` |

**请求示例**

```json
{
  "prompt": "一首关于夏天海边的日系摇滚，节奏明快",
  "lyrics": "蓝天白云下 浪花拍打岸边...",
  "is_instrumental": false,
  "model_used": "music-2.6"
}
```

**SSE 事件流**

同 3.1，`song.source_type` 为 `prompt`，`song.source_url` 为 null。

---

## 4. 语音转文字模块 (ASR)

### 4.1 语音转文字

将音频文件中的语音内容转为文字。支持中英文等多语言识别。

```
POST /asr/transcribe
```

**请求头**

| Header | 值 |
|--------|---|
| Authorization | Bearer {token} |
| Content-Type | multipart/form-data |

**请求体（form-data）**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 音频文件，支持 mp3/wav/m4a/ogg，最大 50MB |
| language | string | 否 | 期望识别的语言代码，如 `zh`、`en`、`ja`，默认自动检测 |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "text": "今天天气真好，我想写一首关于阳光的歌曲",
    "language": "zh",
    "duration": 5.2
  }
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| text | string | 识别出的文字内容 |
| language | string | 识别到的语言代码 |
| duration | number | 音频时长（秒） |

**错误码**

| code | 说明 |
|------|------|
| 400 | 文件格式不支持或文件过大 |
| 422 | 音频内容无法识别（静音或噪音过大） |

---

### 4.2 实时语音转文字（WebSocket）

用于前端把实时音频帧推给后端，由后端桥接到讯飞 RTASR，再把增量识别结果回推给前端。

```
WS /asr/stream?language=zh
```

**连接地址示例**

```text
ws://localhost:8000/v1/asr/stream?language=zh
```

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| language | string | 否 | 期望识别语言，默认 `zh` |

**客户端 -> 服务端消息**

- 二进制帧：音频数据分片
- 文本帧 `__end__`：表示音频流结束

**服务端 -> 客户端消息**

1. 连接建立后首先返回：

```json
{
  "event": "started",
  "language": "zh"
}
```

2. 增量识别结果：

```json
{
  "event": "result",
  "text": "今天天气真好",
  "is_final": false,
  "raw": { "...": "上游原始消息，可选" }
}
```

3. 上游错误透传：

```json
{
  "event": "error",
  "text": "engine error|37005:Client idle timeout",
  "raw": { "...": "上游原始错误" }
}
```

**说明**

- 该接口是 WebSocket，不是普通 HTTP 接口。
- 当前后端会把上游讯飞消息转成 `started / result / error / raw` 四类事件。
- 若发送静音或无效音频帧，上游可能直接返回错误事件并关闭连接。

---

## 5. 歌曲管理模块 (Songs)

### 5.1 我的歌曲列表

获取当前用户的所有歌曲，支持分页和状态筛选。

```
GET /songs
```

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页数量，默认 20，最大 50 |
| status | string | 否 | 筛选状态：`pending`、`processing`、`done`、`failed` |
| source_type | string | 否 | 筛选来源：`image`、`voice`、`prompt` |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "source_type": "image",
        "status": "done",
        "title": "夏日海风",
        "description":"一首和海风有关的歌",
        "cover_url": "https://cdn.world-echo.com/covers/xxx.jpg",
        "music_url": "https://cdn.world-echo.com/music/xxx.mp3",
        "is_instrumental": false,
        "is_public": false,
        "likes_count": 12,
        "created_at": "2026-05-01T12:00:00Z"
      }
    ],
    "total": 35,
    "page": 1,
    "page_size": 20
  }
}
```

---

### 5.2 歌曲详情

获取单首歌曲的完整信息。

```
GET /songs/{id}
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string (UUID) | 是 | 歌曲 ID |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "source_type": "image",
    "extracted_data": {
      "scene": "海边",
      "mood": "cheerful",
      "bpm": 120
    },
    "model_used": "music-2.6",
    "prompt": "温暖的民谣风格",
    "lyrics": "蓝天白云下 浪花拍打岸边...",
    "is_instrumental": false,
    "source_url": "https://cdn.world-echo.com/uploads/images/xxx.jpg",
    "title": "夏日海风",
    "description":"一首和海风有关的歌",
    "status": "done",
    "music_url": "https://cdn.world-echo.com/music/xxx.mp3",
    "cover_url": "https://cdn.world-echo.com/covers/xxx.jpg",
    "error_msg": null,
    "is_public": false,
    "published_at": null,
    "likes_count": 12,
    "created_at": "2026-05-01T12:00:00Z",
    "updated_at": "2026-05-01T12:02:30Z"
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 404 | 歌曲不存在 |
| 403 | 无权查看他人未发布的歌曲 |

---

### 5.3 修改歌曲信息

修改歌曲的展示信息（仅限本人且状态为 done 的歌曲）。

```
PUT /songs/{id}
```

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 否 | 歌曲标题，1-200 字符 |
| description | string | 否 | 歌曲描述 |

**请求示例**

```json
{
  "title": "夏日海风（修改版）",
  "description": "新的歌曲描述..."
}
```

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "title": "夏日海风（修改版）",
    "description": "新的歌曲描述...",
    "updated_at": "2026-05-01T14:00:00Z"
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 404 | 歌曲不存在 |
| 403 | 无权修改他人歌曲 |
| 422 | 歌曲尚未生成完成 |

---

### 5.4 删除歌曲

软删除歌曲，可恢复。

```
DELETE /songs/{id}
```

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

**错误码**

| code | 说明 |
|------|------|
| 404 | 歌曲不存在 |
| 403 | 无权删除他人歌曲 |

---

### 5.5 发布/取消发布到广场

将歌曲发布到歌曲广场或从广场撤回。

```
PUT /songs/{id}/publish
```

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| is_public | boolean | 是 | true 发布到广场，false 从广场撤回 |

**请求示例**

```json
{
  "is_public": true
}
```

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "is_public": true,
    "published_at": "2026-05-01T15:00:00Z"
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 404 | 歌曲不存在 |
| 403 | 无权操作他人歌曲 |
| 422 | 歌曲尚未生成完成，无法发布 |

---

## 6. 歌单模块 (Playlists)

### 6.1 我的歌单列表

获取当前用户的所有歌单。

```
GET /playlists
```

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "title": "我的收藏",
        "description":"这是我的一个歌单",
        "cover_url": null,
        "is_public": false,
        "is_default": true,
        "songs_count": 15,
        "created_at": "2026-05-01T12:00:00Z"
      },
      {
        "id": 2,
        "title": "运动歌单",
        "cover_url": "https://cdn.world-echo.com/playlists/xxx.jpg",
        "is_public": true,
        "is_default": false,
        "songs_count": 8,
        "created_at": "2026-05-01T13:00:00Z"
      }
    ],
    "total": 2
  }
}
```

---

### 6.2 创建歌单

```
POST /playlists
```

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 歌单名称，1-100 字符 |
| description | string | 否 | 歌单描述 |
| cover_url | string | 否 | 封面图 URL |
| is_public | boolean | 否 | 是否公开，默认 false |

**请求示例**

```json
{
  "title": "深夜治愈系",
  "description":"这是我的一个歌单",
  "cover_url": "https://cdn.world-echo.com/playlists/xxx.jpg",
  "is_public": true
}
```

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 3,
    "title": "深夜治愈系",
    "description":"这是我的一个歌单",
    "cover_url": "https://cdn.world-echo.com/playlists/xxx.jpg",
    "is_public": true,
    "is_default": false,
    "songs_count": 0,
    "created_at": "2026-05-01T16:00:00Z",
    "updated_at": "2026-05-01T16:00:00Z"
  }
}
```

---

### 6.3 歌单详情

获取歌单详情及其包含的歌曲列表。

```
GET /playlists/{id}
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | integer | 是 | 歌单 ID |

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | integer | 否 | 歌曲页码，默认 1 |
| page_size | integer | 否 | 每页数量，默认 20 |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 2,
    "title": "运动歌单",
    "description":"这是我的一个歌单",
    "cover_url": "https://cdn.world-echo.com/playlists/xxx.jpg",
    "is_public": true,
    "is_default": false,
    "created_at": "2026-05-01T13:00:00Z",
    "updated_at": "2026-05-01T14:00:00Z",
    "songs": {
      "items": [
        {
          "playlist_item_id": 10,
          "sort_order": 0,
          "added_at": "2026-05-01T13:30:00Z",
          "song": {
            "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
            "title": "夏日海风",
            "description":"这是一首歌",
            "cover_url": "https://cdn.world-echo.com/covers/xxx.jpg",
            "music_url": "https://cdn.world-echo.com/music/xxx.mp3",
            "source_type": "image",
            "likes_count": 12
          }
        }
      ],
      "total": 8,
      "page": 1,
      "page_size": 20
    }
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 404 | 歌单不存在 |
| 403 | 无权查看他人私有歌单 |

---

### 6.4 编辑歌单

```
PUT /playlists/{id}
```

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 否 | 歌单名称 |
| description | string | 否 | 歌单描述 |
| cover_url | string | 否 | 封面图 URL |
| is_public | boolean | 否 | 是否公开 |

**请求示例**

```json
{
  "title": "运动歌单 v2",
  "description":"这是我的一个歌单",
  "is_public": false
}
```

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 2,
    "title": "运动歌单 v2",
    "description":"这是我的一个歌单",
    "cover_url": "https://cdn.world-echo.com/playlists/xxx.jpg",
    "is_public": false,
    "is_default": false,
    "updated_at": "2026-05-01T17:00:00Z"
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 404 | 歌单不存在 |
| 403 | 无权编辑他人歌单 |

---

### 6.5 删除歌单

软删除歌单。默认歌单（is_default=true）不可删除。

```
DELETE /playlists/{id}
```

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

**错误码**

| code | 说明 |
|------|------|
| 404 | 歌单不存在 |
| 403 | 无权删除他人歌单 |
| 422 | 默认歌单不可删除 |

---

### 6.6 添加歌曲到歌单

将歌曲添加到指定歌单。同一首歌不能重复添加到同一歌单。

```
POST /playlists/{id}/songs
```

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| song_id | string (UUID) | 是 | 要添加的歌曲 ID |

**请求示例**

```json
{
  "song_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"
}
```

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 11,
    "playlist_id": 2,
    "song_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "sort_order": 1,
    "added_at": "2026-05-01T18:00:00Z"
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 404 | 歌单或歌曲不存在 |
| 403 | 无权操作他人歌单 |
| 409 | 歌曲已在歌单中 |

---

### 6.7 从歌单移除歌曲

```
DELETE /playlists/{id}/songs/{songId}
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | integer | 是 | 歌单 ID |
| songId | string (UUID) | 是 | 歌曲 ID |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

**错误码**

| code | 说明 |
|------|------|
| 404 | 歌单不存在或歌曲不在歌单中 |
| 403 | 无权操作他人歌单 |

---

### 6.8 歌单内歌曲排序

批量调整歌单内歌曲的顺序。

```
PUT /playlists/{id}/songs/sort
```

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| song_ids | array[string] | 是 | 按新顺序排列的歌曲 ID 数组 |

**请求示例**

```json
{
  "song_ids": [
    "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "d4e5f6a7-b8c9-0123-defa-234567890123"
  ]
}
```

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "sorted_count": 3
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 404 | 歌单不存在 |
| 403 | 无权操作他人歌单 |
| 422 | song_ids 包含不属于该歌单的歌曲 |

---

## 7. 歌曲广场模块 (Plaza)

### 7.1 广场歌曲流

获取歌曲广场的公开歌曲列表，按发布时间倒序排列。

```
GET /plaza
```

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页数量，默认 20，最大 50 |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "title": "夏日海风",
        "description":"这是我的一首歌",
        "cover_url": "https://cdn.world-echo.com/covers/xxx.jpg",
        "music_url": "https://cdn.world-echo.com/music/xxx.mp3",
        "source_type": "image",
        "is_instrumental": false,
        "likes_count": 12,
        "is_liked": true,
        "published_at": "2026-05-01T15:00:00Z",
        "user": {
          "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          "username": "music_lover",
          "avatar_url": "https://cdn.world-echo.com/avatars/xxx.jpg"
        }
      }
    ],
    "total": 150,
    "page": 1,
    "page_size": 20
  }
}
```

**说明**
- `is_liked` 表示当前登录用户是否已点赞（未登录时为 false）
- `user` 为歌曲作者的简要信息

---

### 7.2 广场歌曲详情

查看广场中某首歌曲的完整信息。

```
GET /plaza/{id}
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string (UUID) | 是 | 歌曲 ID |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "title": "夏日海风",
    "description":"这是我的一首歌",
    "cover_url": "https://cdn.world-echo.com/covers/xxx.jpg",
    "music_url": "https://cdn.world-echo.com/music/xxx.mp3",
    "source_type": "image",
    "model_used": "music-2.6",
    "prompt": "温暖的民谣风格",
    "lyrics": "蓝天白云下 浪花拍打岸边...",
    "is_instrumental": false,
    "likes_count": 12,
    "is_liked": true,
    "published_at": "2026-05-01T15:00:00Z",
    "user": {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "username": "music_lover",
      "avatar_url": "https://cdn.world-echo.com/avatars/xxx.jpg"
    },
    "created_at": "2026-05-01T12:00:00Z"
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 404 | 歌曲不存在或未发布到广场 |

---

## 8. 点赞模块 (Favorites)

### 8.1 点赞

对广场歌曲点赞。同一用户对同一首歌只能点赞一次（软删除后可重新点赞）。

```
POST /favorites/{songId}
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| songId | string (UUID) | 是 | 歌曲 ID |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 50,
    "song_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "created_at": "2026-05-01T19:00:00Z"
  }
}
```

**错误码**

| code | 说明 |
|------|------|
| 404 | 歌曲不存在 |
| 409 | 已经点赞过 |
| 422 | 不能点赞自己的歌曲或歌曲未发布 |

---

### 8.2 取消点赞

```
DELETE /favorites/{songId}
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| songId | string (UUID) | 是 | 歌曲 ID |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

**错误码**

| code | 说明 |
|------|------|
| 404 | 歌曲不存在或未点赞 |
