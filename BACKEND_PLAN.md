# World Echo Backend Plan

## Summary

- [x] Phase 1: Create project skeleton, `BACKEND_PLAN.md`, `PROGRESS.md`, base FastAPI app, config, ORM models, common infrastructure.
- [x] Phase 2: Implement auth and upload modules.
- [x] Phase 3: Implement songs, playlists, plaza, favorites, ASR, SSE generation, external service adapters.
- [x] Phase 4: Add tests, Docker/dev setup, README, verification, final cleanup.
- [x] Phase 5: Validate available real third-party integrations and fix runtime mismatches.
- [x] Phase 6: Add normal register/login auth, sync API docs/OpenAPI JSON, and validate generation endpoints with curated test files.

## Module Breakdown

- [x] Core infrastructure: config, logging, exceptions, unified responses, auth dependency, static file mounting.
- [x] Data layer: async SQLAlchemy session, ORM models, query helpers, DB init.
- [x] Auth: OAuth URL, callback, logout, current user, profile update, default playlist bootstrap.
- [x] Upload: image upload, audio upload, local storage abstraction, public static URLs.
- [x] ASR: file transcription API and realtime WebSocket bridge.
- [x] Generation: prompt/image/voice SSE flows, MiniMax adapter, prompt refinement, analysis orchestration.
- [x] Song management: list, detail, update, soft delete, publish/unpublish.
- [x] Playlist management: CRUD, add/remove songs, sort.
- [x] Plaza and favorites: public feed, detail, like/unlike.
- [x] Engineering: Docker, environment config, README, tests.

## API Implementation Order

- [x] Base app and DB bootstrap.
- [x] Auth endpoints.
- [x] Upload endpoints.
- [x] Song CRUD endpoints.
- [x] Playlist endpoints.
- [x] Plaza and favorite endpoints.
- [x] ASR HTTP and WebSocket endpoints.
- [x] SSE generation endpoints.
- [x] Test suite and local runtime packaging.

## Database Mapping

- [x] `users` <-> `User`
- [x] `user_oauths` <-> `UserOAuth`
- [x] `songs` <-> `Song`
- [x] `playlists` <-> `Playlist`
- [x] `playlist_items` <-> `PlaylistItem`
- [x] `favorites` <-> `Favorite`

## SSE Generation Scheme

- [x] Persist `songs` record before streaming with `pending` status.
- [x] Transition to `processing` before external generation starts.
- [x] Stream MiniMax chunks as `status=1` events with `audio_hex`.
- [x] Persist final audio, metadata, `music_url`, `cover_url`, `description`, `extracted_data`, `status=done`.
- [x] Emit final `status=2` event with full song payload.
- [x] On failure, persist `status=failed`, `error_msg`, emit `status=3`.

## Mock External Services

- [x] Mock OAuth provider.
- [x] Mock ASR service and mock realtime bridge.
- [x] Mock vision prompt service.
- [x] Mock audio analysis service.
- [x] Mock prompt refiner service.
- [x] Mock MiniMax streaming service.

## Test Plan

- [x] Unit tests for config, JWT, responses, exceptions, service rules.
- [x] API tests for auth, upload, songs, playlists, plaza, favorites, ASR.
- [x] SSE tests for prompt/image/voice generation flows.
- [x] WebSocket tests for realtime ASR bridge.
- [x] Mock-mode integration tests.

## Real Integration Validation

- [x] Use `Qwen/Qwen3-VL-32B-Instruct` for SiliconFlow multimodal image analysis.
- [x] Replace the audio prompt refiner template with the `audio_to_music_prompt.py` prompt and validate the real SiliconFlow call path.
- [x] Validate the real MiniMax stream shape and patch the adapter to support status-less audio chunks plus final `[DONE]` synthesis.
- [x] Validate the real image generation SSE chain to a final `status=2` event.
- [x] Validate the real XFYun RTASR WebSocket bridge handshake and error forwarding, and fix close-path `500` handling.
- [ ] Validate real GitHub OAuth callback flow.
- [ ] Validate real QQ OAuth callback flow.
- [ ] Validate real file transcription flow for `/v1/asr/transcribe`.
- [x] Validate fully real voice-generation flow with `ENABLE_ESSENTIA=true` and non-mock audio analysis.

## Auth And Docs Sync

- [x] Add `/auth/register` for username/email/password signup.
- [x] Add `/auth/login` for username-or-email plus password signin.
- [x] Persist password hashes on `users.password_hash`.
- [x] Update `database/init.sql` and runtime DB bootstrap for the new auth column.
- [x] Sync `docs/API-DOCS.md` with the new auth endpoints and the XFYun realtime WebSocket interface.
- [x] Sync `docs/world-echo-api.json` with the new auth endpoints and a path-level `x-websocket` description for `/asr/stream`.

## Playback Validation

- [x] Re-run `prompt`, `image`, and `voice` generation endpoints with files from `test-files/`.
- [x] Skip direct ASR endpoint smoke tests during this playback pass.
- [x] Copy generated music outputs into a single local playback directory for manual review.
- [x] Validate `music-cover` against a public remote audio URL and copy the result into the same playback directory.
- [x] Rebuild the local virtual environment on Python 3.11, install `essentia-tensorflow`, and validate the real Essentia -> SiliconFlow -> MiniMax `voice` flow with `test-files/test-environmental-sound.m4a`.

## Risks

- [ ] Essentia runtime and model loading can be heavy; keep fallback path.
- [ ] MiniMax stream protocol details may differ from docs; isolate in adapter.
- [ ] Realtime ASR needs careful WebSocket lifecycle handling.
- [ ] SSE disconnects can leave long-running tasks in inconsistent states without cleanup.
- [ ] `likes_count` is maintained in service code and needs transactional handling.
