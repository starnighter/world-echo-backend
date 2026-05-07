# World Echo Backend Plan

## Summary

- [x] Phase 1: Create project skeleton, `BACKEND_PLAN.md`, `PROGRESS.md`, base FastAPI app, config, ORM models, common infrastructure.
- [ ] Phase 2: Implement auth and upload modules.
- [ ] Phase 3: Implement songs, playlists, plaza, favorites, ASR, SSE generation, external service adapters.
- [ ] Phase 4: Add tests, Docker/dev setup, README, verification, final cleanup.

## Module Breakdown

- [x] Core infrastructure: config, logging, exceptions, unified responses, auth dependency, static file mounting.
- [x] Data layer: async SQLAlchemy session, ORM models, query helpers, DB init.
- [ ] Auth: OAuth URL, callback, logout, current user, profile update, default playlist bootstrap.
- [ ] Upload: image upload, audio upload, local storage abstraction, public static URLs.
- [ ] ASR: file transcription API and realtime WebSocket bridge.
- [ ] Generation: prompt/image/voice SSE flows, MiniMax adapter, prompt refinement, analysis orchestration.
- [ ] Song management: list, detail, update, soft delete, publish/unpublish.
- [ ] Playlist management: CRUD, add/remove songs, sort.
- [ ] Plaza and favorites: public feed, detail, like/unlike.
- [ ] Engineering: Docker, environment config, README, tests.

## API Implementation Order

- [x] Base app and DB bootstrap.
- [ ] Auth endpoints.
- [ ] Upload endpoints.
- [ ] Song CRUD endpoints.
- [ ] Playlist endpoints.
- [ ] Plaza and favorite endpoints.
- [ ] ASR HTTP and WebSocket endpoints.
- [ ] SSE generation endpoints.
- [ ] Test suite and local runtime packaging.

## Database Mapping

- [x] `users` <-> `User`
- [x] `user_oauths` <-> `UserOAuth`
- [x] `songs` <-> `Song`
- [x] `playlists` <-> `Playlist`
- [x] `playlist_items` <-> `PlaylistItem`
- [x] `favorites` <-> `Favorite`

## SSE Generation Scheme

- [ ] Persist `songs` record before streaming with `pending` status.
- [ ] Transition to `processing` before external generation starts.
- [ ] Stream MiniMax chunks as `status=1` events with `audio_hex`.
- [ ] Persist final audio, metadata, `music_url`, `cover_url`, `description`, `extracted_data`, `status=done`.
- [ ] Emit final `status=2` event with full song payload.
- [ ] On failure, persist `status=failed`, `error_msg`, emit `status=3`.

## Mock External Services

- [ ] Mock OAuth provider.
- [ ] Mock ASR service and mock realtime bridge.
- [ ] Mock vision prompt service.
- [ ] Mock audio analysis service.
- [ ] Mock prompt refiner service.
- [ ] Mock MiniMax streaming service.

## Test Plan

- [ ] Unit tests for config, JWT, responses, exceptions, service rules.
- [ ] API tests for auth, upload, songs, playlists, plaza, favorites, ASR.
- [ ] SSE tests for prompt/image/voice generation flows.
- [ ] WebSocket tests for realtime ASR bridge.
- [ ] Mock-mode integration tests.

## Risks

- [ ] Essentia runtime and model loading can be heavy; keep fallback path.
- [ ] MiniMax stream protocol details may differ from docs; isolate in adapter.
- [ ] Realtime ASR needs careful WebSocket lifecycle handling.
- [ ] SSE disconnects can leave long-running tasks in inconsistent states without cleanup.
- [ ] `likes_count` is maintained in service code and needs transactional handling.
