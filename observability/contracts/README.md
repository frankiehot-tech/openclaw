# Athena Observability Adapter Contracts

These schemas define the P0-1 read-only adapter contract for Athena runtime
observability.

Goals:
- Reuse current local truth sources instead of inventing new state.
- Make empty/stale/unavailable states explicit.
- Keep the contract implementation-oriented so adapter work can start
  immediately.

Contract version:
- `athena-observability.v1-draft`

Primary truth sources expected by the adapter:
- `/Volumes/1TB-M2/openclaw/scripts/openclaw_roots.py`
- `/Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py`
- `/Volumes/1TB-M2/openclaw/scripts/system_resource_facts.py`
- `/Volumes/1TB-M2/openclaw/.openclaw/orchestrator/tasks.json`
- `/Volumes/1TB-M2/openclaw/.openclaw/orchestrator/tasks/*/trace.json`
- `/Volumes/1TB-M2/openclaw/mini-agent/agent/core/chat_runtime.py`

## Endpoint Mapping

- `GET /health`
  - Schema: `health.schema.json`
- `GET /v1/system/facts`
  - Schema: `system-facts.schema.json`
- `GET /v1/queues`
  - Schema: `queues.schema.json`
- `GET /v1/tasks/recent`
  - Schema: `tasks-recent.schema.json`
- `GET /v1/tasks/{taskId}/trace`
  - Schema: `task-trace.schema.json`
- `GET /v1/tasks/{taskId}/artifact`
  - Schema: `task-artifact.schema.json`
- `GET /v1/chat/status`
  - Schema: `chat-status.schema.json`
- `GET /v1/agents`
  - Schema: `agents.schema.json`
- `GET /v1/node-graph`
  - Schema: `node-graph.schema.json`

## Contract Rules

- Every response must include:
  - `contractVersion`
  - `generatedAt`
  - `runtimeRoot`
  - `source`
  - `freshness`
- `freshness` meanings:
  - `live`: generated from current runtime evidence
  - `stale`: last known data exists but probe/snapshot is old
  - `unavailable`: upstream truth source could not be loaded
- The adapter must not silently substitute demo data.
- Missing data should be explicit:
  - `found=false`
  - `message`
  - `warnings[]`
  - empty arrays instead of absent collections

## Compatibility Notes

- `queues.schema.json` is intentionally close to the current
  `/api/athena/queues` payload from `athena_web_desktop_compat.py`.
- `task-trace.schema.json` matches the real `trace.json` files already written
  by `athena_orchestrator.py`.
- `system-facts.schema.json` exposes both:
  - top/PhysMem style memory facts
  - memory pressure / runner gate facts
  This avoids the previous ambiguity where one percentage tried to represent
  multiple memory meanings.

## Field Normalization Notes

Current truth sources are mostly snake_case. The adapter contract normalizes
public fields to camelCase.

Key mappings to preserve during implementation:

- Queues:
  - `route_id -> routeId`
  - `queue_id -> queueId`
  - `current_item_id -> currentItemId`
  - `current_item_ids -> currentItemIds`
  - `queue_status -> queueStatus`
  - `pause_reason -> pauseReason`
  - `next_action_hint -> nextActionHint`
  - `entry_stage -> entryStage`
  - `risk_level -> riskLevel`
  - `instruction_path -> instructionPath`
  - `root_task_id -> rootTaskId`
  - `artifact_path -> artifactPath`
  - `result_excerpt -> resultExcerpt`
  - `pipeline_summary -> pipelineSummary`
  - `artifact_paths -> artifactPaths`
  - `progress_percent -> progressPercent`
  - `expected_stages -> expectedStages`
  - `current_stage_ids -> currentStageIds`
  - `runner_pid -> runnerPid`
  - `runner_heartbeat_at -> runnerHeartbeatAt`
  - `manual_override_autostart -> manualOverrideAutostart`
  - `is_current -> isCurrent`
- Tasks:
  - `queue_item_id -> queueItemId`
  - `instruction_path -> instructionPath`
  - `artifact_path -> artifactPath`
  - `created_at -> createdAt`
  - `started_at -> startedAt`
  - `finished_at -> finishedAt`
  - `updated_at -> updatedAt`
- Trace:
  - `artifact_type -> artifactType`
  - `status_changes -> statusChanges`
  - `created_at -> createdAt`
- Chat runtime:
  - `chat_state -> chatState`
  - `chat_backend -> chatBackend`
  - `chat_selected_model -> chatSelectedModel`
  - `chat_reason -> chatReason`
  - `chat_primary -> chatPrimary`
  - `chat_fallback -> chatFallback`
  - `degraded_reason -> degradedReason`
