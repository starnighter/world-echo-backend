-- ==========================================
-- 1. 账户与鉴权体系 (Auth)
-- ==========================================

-- 用户主表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    avatar_url TEXT,
    is_banned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 第三方授权表
CREATE TABLE user_oauths (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(20) NOT NULL, -- e.g., 'github', 'qq'
    provider_uid VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, provider_uid) -- 同一个第三方账号只能绑定一个用户
);
CREATE INDEX idx_user_oauths_user ON user_oauths(user_id);

-- ==========================================
-- 2. 核心业务：歌曲 (Songs)
-- ==========================================

-- 歌曲表（生成任务 = 歌曲实体）
CREATE TABLE songs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('image', 'voice', 'prompt')),
    extracted_data JSONB, -- 中间分析结果 (如 ASR文本, Essentia提取的BPM/情绪)

    -- 模型与参数配置
    model_used VARCHAR(50) NOT NULL, -- e.g., 'music-2.6', 'music-cover'
    prompt TEXT,
    lyrics TEXT,
    is_instrumental BOOLEAN DEFAULT FALSE,
    source_url TEXT, -- 原始上传文件（图片或语音），prompt 模式下为 NULL

    -- 展示信息
    title VARCHAR(200), -- 歌曲展示名称，生成完成后由 AI 或用户填入
    cover_url TEXT, -- 歌曲封面图 URL，由系统后端生成
    description TEXT DEFAULT NULL, -- 歌曲描述，生成之后默认为空

    -- 状态与结果
    status VARCHAR(20) DEFAULT 'pending' NOT NULL CHECK (status IN ('pending', 'processing', 'done', 'failed')),
    music_url TEXT, -- 最终生成的音乐链接 (OSS)
    error_msg TEXT,

    -- 广场发布
    is_public BOOLEAN DEFAULT FALSE, -- 是否发布到歌曲广场
    published_at TIMESTAMP WITH TIME ZONE, -- 发布时间，用于广场排序

    -- 社交数据
    likes_count INT DEFAULT 0, -- 点赞计数（交由后端服务层逻辑维护）

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);
CREATE INDEX idx_songs_user ON songs(user_id);
CREATE INDEX idx_songs_status ON songs(status);
CREATE INDEX idx_songs_plaza ON songs(is_public, published_at DESC)
    WHERE is_public = TRUE AND deleted_at IS NULL;
CREATE INDEX idx_songs_active ON songs(user_id) WHERE deleted_at IS NULL;

-- ==========================================
-- 3. 歌单管理 (Playlists)
-- ==========================================

-- 歌单表
CREATE TABLE playlists (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description TEXT DEFAULT NULL, -- 歌单描述，生成之后默认为空
    cover_url TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    is_default BOOLEAN DEFAULT FALSE, -- 标记每个用户的"我的收藏"默认歌单
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);
CREATE INDEX idx_playlists_user ON playlists(user_id);
-- 确保每用户最多一个默认歌单
CREATE UNIQUE INDEX idx_one_default_playlist
    ON playlists(user_id)
    WHERE is_default = TRUE AND deleted_at IS NULL;

-- 歌单明细关联表
CREATE TABLE playlist_items (
    id BIGSERIAL PRIMARY KEY,
    playlist_id BIGINT NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    song_id UUID NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    sort_order INT DEFAULT 0,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(playlist_id, song_id) -- 防止同一首歌重复添加到同一个歌单
);
CREATE INDEX idx_playlist_items_playlist ON playlist_items(playlist_id);
CREATE INDEX idx_playlist_items_song ON playlist_items(song_id);

-- ==========================================
-- 4. 点赞 (Favorites)
-- ==========================================

-- 点赞表（用于广场歌曲点赞，点赞数同步到 songs.likes_count）
CREATE TABLE favorites (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    song_id UUID NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);
CREATE INDEX idx_favorites_user ON favorites(user_id);
CREATE INDEX idx_favorites_song ON favorites(song_id);
-- 部分唯一索引：保证同一用户对同一首歌只有一次有效点赞，软删除后允许重新点赞
CREATE UNIQUE INDEX idx_favorites_user_song_active
    ON favorites(user_id, song_id)
    WHERE deleted_at IS NULL;

-- ==========================================
-- 5. 更新时间戳触发器
-- ==========================================
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_modtime BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_songs_modtime BEFORE UPDATE ON songs FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_playlists_modtime BEFORE UPDATE ON playlists FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_favorites_modtime BEFORE UPDATE ON favorites FOR EACH ROW EXECUTE FUNCTION update_modified_column();
