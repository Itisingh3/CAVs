# Consensus signing (v1.0.0)

`REQUEST`, `PRE-PREPARE`, `PREPARE`, `RESPONSE`, and `REPLY` messages are signed with ML-DSA-65. A signed consensus payload contains: `domain = CAV-CONSENSUS-v1`, message type, view, sequence number, block/transaction digest, sender pseudonym, timestamp, and algorithm identifiers.

Receivers verify the sender credential, algorithm identifiers, signature, view/sequence freshness, and transaction digest before counting a message. A node may count at most one valid message from a pseudonym for a `(view, sequence, type)` tuple. The leader executes only after at least `2f+1` distinct valid responses; the deployment must enforce `n >= 3f+1`.

The original paper's undefined `Sign_c`, `Sign_l`, and `Sign_r` tokens are not used.
