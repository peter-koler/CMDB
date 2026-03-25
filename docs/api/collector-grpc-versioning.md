# Collector gRPC Contract Versioning (M0-02 Frozen)

## Contract File

- Primary schema (Collector): `collector-go/proto/collector.proto`
- Primary schema (Manager): `manager-go/proto/collector.proto`
- Package: `collector.v1`
- Service: `CollectorService.Connect(stream CollectorFrame) returns (stream ManagerFrame)`

> **注意**: 两个 proto 文件内容保持一致，Manager 端复制自 Collector 端，确保协议兼容。

## Message Flow

- Manager -> Collector (`CollectorFrame`)
  - `upsert` (full task payload)
  - `delete` (new command envelope)
  - `delete_job_id` (legacy compatibility path, deprecated)
  - `heartbeat`
- Collector -> Manager (`ManagerFrame`)
  - `report` (collect result)
  - `ack` (command acknowledgement state)
  - `heartbeat`

## Ack Semantics

- `CommandAck.command_id`: idempotency and tracing key from manager command.
- `CommandAck.status`:
  - `ACK_STATUS_RECEIVED`: collector accepted frame parsing and queued processing
  - `ACK_STATUS_APPLIED`: collector applied command successfully
  - `ACK_STATUS_REJECTED`: collector rejected command due to validation/runtime issue
  - `ACK_STATUS_NOT_FOUND`: delete target not found
- `reason`: optional diagnostic text for rejected/not found cases.

## Backward Compatibility Rules

1. Do not remove existing fields or change numeric tags.
2. New fields are append-only with new tags.
3. Existing enum values are immutable once released.
4. Deprecated fields remain readable for at least one minor cycle.
5. Oneof extensions can add new alternatives but must not reuse tags.
6. Wire compatibility is mandatory between adjacent minor versions.

## Evolution Strategy

- Current baseline: `collector.v1` with ack coverage.
- Breaking changes require new package version (for example `collector.v2`).
- Non-breaking additions stay in `collector.v1` with regenerated SDK stubs.

## Regeneration Requirement

Any proto contract change must regenerate:

### Collector 端
- `collector-go/internal/pb/collector.pb.go`
- `collector-go/internal/pb/collector_grpc.pb.go`

### Manager 端
- `manager-go/internal/pb/proto/collector.pb.go`
- `manager-go/internal/pb/proto/collector_grpc.pb.go`

before implementation integration and CI verification.

## Implementation Reference

### Manager 端实现
- **Client**: `manager-go/internal/collector/client.go` - 单 Collector 连接管理
- **Manager**: `manager-go/internal/collector/manager.go` - Collector 连接池管理
- **Scheduler**: `manager-go/internal/collector/scheduler.go` - 任务下发调度

### Collector 端实现
- **Server**: `collector-go/internal/transport/grpc_server.go` - gRPC Server 实现
- **Batch Reporter**: `collector-go/internal/transport/batch_reporter.go` - 批量结果上报

### 架构文档
- 详见: `docs/migration-plan.md` 第 13 章 "gRPC 连接架构（Manager ↔ Collector）"
