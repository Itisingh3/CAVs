# Networking-letter tables

`networking-letter-tables.tex` contains the three compact tables for the four-page letter.

| Table | Insert in paper section | Why it belongs there |
| --- | --- | --- |
| Table I, method comparison | Section II-C, Design Goals and Gap Analysis | Establishes the precise delta from the base paper and adjacent PQC-V2X work before protocol detail. |
| Table II, security-property mapping | Section V-C, Formal Security Verification | Connects each security claim to a concrete mechanism and formal-verification target. |
| Table III, measured PQC overhead | Section VI-A, Implementation and Measurement Setup | Separates actual local crypto cost from final simulator/network performance results. |

Table numbering can change automatically when the final IEEE template orders floats differently. Verify every `\cite{...}` key against the final bibliography before compiling.
