# Athena Observability + SigNoz Setup

This adapter can export OTLP traces and metrics to SigNoz while remaining safe
to run locally when SigNoz is absent.

## 1. Install local adapter dependencies

```bash
/Volumes/1TB-M2/openclaw/scripts/install_athena_observability_env.sh
```

This creates:

- `/Volumes/1TB-M2/openclaw/.venvs/athena-observability`

and installs:

- `openlit`
- `opentelemetry-sdk`
- `opentelemetry-exporter-otlp-proto-http`
- `opentelemetry-exporter-otlp-proto-grpc`

## 2. Configure OTLP export

Copy:

- `/Volumes/1TB-M2/openclaw/observability/observability.env.example`

to:

- `/Volumes/1TB-M2/openclaw/.openclaw/observability.env`

Then set these values.

### Self-hosted SigNoz

Use the local collector:

```bash
ATHENA_OBSERVABILITY_OTLP_ENDPOINT=http://127.0.0.1:4318
ATHENA_OBSERVABILITY_OTLP_PROTOCOL=http/protobuf
```

### SigNoz Cloud

Follow SigNoz's official OTLP guidance and set:

```bash
ATHENA_OBSERVABILITY_OTLP_ENDPOINT=https://ingest.<region>.signoz.cloud:443
ATHENA_OBSERVABILITY_OTLP_PROTOCOL=grpc
ATHENA_OBSERVABILITY_OTLP_HEADERS=signoz-ingestion-key=<your-ingestion-key>
```

## 3. Start the adapter service

```bash
/Volumes/1TB-M2/openclaw/scripts/start_athena_observability_adapter.sh
```

Check:

```bash
/Volumes/1TB-M2/openclaw/scripts/status_athena_observability_adapter.sh
curl -s http://127.0.0.1:8090/health | jq
```

## 4. What is exported

Current P0 signals:

- Adapter HTTP request spans
- Request count metric
- Error count metric
- Request duration histogram

Current attributes:

- `http.route`
- `http.method`
- `http.status_code`
- `athena.runtime_root`
- `athena.adapter.source`
- `athena.adapter.freshness`

## 5. Current limitations

- The adapter now exports its own telemetry, but runner/chat/orchestrator spans
  still need to be instrumented in later steps.
- If OTLP is not configured, the adapter still runs normally in read-only local
  mode.

## References

- [OpenLIT installation](https://docs.openlit.io/latest/openlit/installation)
- [SigNoz Python OpenTelemetry instrumentation](https://signoz.io/docs/instrumentation/opentelemetry-python/)
