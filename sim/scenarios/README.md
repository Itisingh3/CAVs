# Final simulator integration contract

The lightweight Python runner exists only for logic development and CI-like smoke tests. It must not be presented as SUMO/Veins/OMNeT++ results.

For the final experiment, an adapter must map a Veins/OMNeT++ window to the JSONL schema emitted by `sim.run_experiment`:

- `network`: density, PDR, latency, mobility/link-quality, packet loss, and traffic load;
- `score_update`: node, agreement result, delta, score;
- `group_transition` / `reassignment` / `ml_reassignment` / `ml_fallback`;
- `metric`: per-window end-to-end and consensus latency, throughput, PDR, control-byte overhead, group churn, malicious-removal time, and honest false-removal rate.

Each final run must save its SUMO seed, OMNeT++ seed, complete scenario configuration, raw simulator outputs, dependency versions, and source revision identifier. Use `sim.seed_manager.split_seeds()` before any tuning and run at least 30 paired test seeds per reported scenario.
