# ML-adaptive grouping interface (v1.0.0)

At the end of every evaluation window, each node produces the feature vector:

`[agreement_rate, normalized_rtt, pdr, link_quality, score_trend, recent_fault_rate]`.

The online logistic model outputs `P(reliable in next window)` per node. Aggregate congestion is the mean of `1 - pdr` and normalized RTT across eligible nodes. Nodes are ranked by reliability and selected subject to `n >= 3f+1`; group size increases under predicted congestion/high load and is otherwise kept near the configured minimum.

Model confidence is `abs(p - 0.5) * 2`, averaged across eligible nodes. If it is below `0.20`, if fewer than 10 labeled observations exist, or if any required feature is invalid, the fallback guard must use the best ablated static configuration. Every fallback is a structured event.

The model is updated only after labels for the current window are observed. Training/validation/test seed separation is enforced by `sim.seed_manager`; final test labels must not tune hyperparameters.
