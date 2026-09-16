# Archived live evidence

`otel-live-run.json` records a genuine local inference performed on 2026-09-16 with synthetic
merchant data, the gateway backend and OpenTelemetry enabled in both lab processes. It preserves
the request, the two actual API responses, curl timings and normalized spans retrieved from Tempo.

Verified facts:

- First execution: HTTP 200, `completed`, `specialist_reused=false`, 6.544756 seconds.
- Replay with the same IDs: HTTP 200, `completed`, `specialist_reused=true`, 0.084811 seconds.
- The two responses have identical summaries.
- Trace `553921e6193daaaa264e37d077dba594` has two spans sharing its trace ID.
- Agno's `specialist.handle` references the LangGraph process's `specialist.delegate` as its parent.
- Span attributes contain only `operation`; no prompt, raw payload or credentials were recorded.

`index.html` is a read-only presentation of that archived JSON. Open it from a local HTTP server:

```bash
cd /path/to/agent-runtime-boundaries-lab
python3 -m http.server 8300 --bind 127.0.0.1 --directory docs/evidence
```

Then visit `http://127.0.0.1:8300`. The report loads only the adjacent evidence file and cannot invoke
models or delegate work. The first README screenshot comes from this report; the Grafana screenshot
comes from the actual Tempo data source in Grafana Explore. The report's trace view provides a
readable rendering of the archived spans.

The test used temporary API/Agno ports 8203/8201 to keep the existing 8003/8101 services running.
The A2A boundary is instrumented; this trace contains no gateway/provider spans or whole-workflow
span. The durations include the specialist's inference path but are not a framework benchmark.

The archive remains available after the local Tempo container is removed. It does not inject traces
into a backend or manufacture runtime evidence. Provider choice/model IDs were not preserved by the
specialist contract, so this record makes no claim about them.
