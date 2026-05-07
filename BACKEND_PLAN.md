# World Echo Backend Plan

## Summary

- [x] Phase 1: Create project skeleton, `BACKEND_PLAN.md`, `PROGRESS.md`, base FastAPI app, config, ORM models, common infrastructure.
- [x] Phase 2: Implement auth and upload modules.
- [x] Phase 3: Implement songs, playlists, plaza, favorites, ASR, SSE generation, external service adapters.
- [x] Phase 4: Add tests, Docker/dev setup, README, verification, final cleanup.

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

## Risks

- [ ] Essentia runtime and model loading can be heavy; keep fallback path.
- [ ] MiniMax stream protocol details may differ from docs; isolate in adapter.
- [ ] Realtime ASR needs careful WebSocket lifecycle handling.
- [ ] SSE disconnects can leave long-running tasks in inconsistent states without cleanup.
- [ ] `likes_count` is maintained in service code and needs transactional handling.
