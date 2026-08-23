# Current CAV-PQC Letter Reference Shortlist

Search cutoff: **21 August 2026**. This is a relevance-filtered, bibliographically verified shortlist for the four-page networking letter, not a claim to enumerate every publication worldwide. Use the **core** set in the letter; reserve the contextual sources for claims that need them. Before submission, rerun the search and verify the final venue's reference style and DOI metadata.

## Core sources (cite in the four-page letter)

1. A. M. Aslam, A. Bhardwaj, and R. Chaudhary, “Quantum-resilient blockchain-enabled secure communication framework for connected autonomous vehicles using post-quantum cryptography,” *Vehicular Communications*, vol. 52, Art. no. 100880, 2025, doi: [10.1016/j.vehcom.2025.100880](https://doi.org/10.1016/j.vehcom.2025.100880).
   - **Use:** Direct baseline and motivation. Cite its stated limitations/future work carefully; do not repeat its undefined-signature construction.

2. W. Wang and S. F. Tan, “Secure V2X Communication in the Quantum Era: A Survey of Post-Quantum Authentication and Key Agreement (AKA) Protocols for Autonomous Vehicles,” *Future Internet*, vol. 18, no. 6, Art. no. 319, 2026, doi: [10.3390/fi18060319](https://doi.org/10.3390/fi18060319).
   - **Use:** Latest V2X PQC/AKA survey; motivate latency, payload, and embedded-resource constraints.

3. I. Rasheed and H. Mostafa, “DAME-IoV: Dynamic Adaptive Multi-Edge authentication protocol with post-quantum security for Internet of Vehicles,” *Vehicular Communications*, vol. 54, Art. no. 100933, 2025, doi: [10.1016/j.vehcom.2025.100933](https://doi.org/10.1016/j.vehcom.2025.100933).
   - **Use:** Recent PQC IoV authentication and adaptive/edge comparison point.

4. D. Mishra and P. Rewal, “A blockchain-based quantum-secure protocol for efficient V2I handover authentication in vehicular Ad-Hoc networks,” *Peer-to-Peer Networking and Applications*, vol. 18, Art. no. 304, 2025, doi: [10.1007/s12083-025-02142-1](https://doi.org/10.1007/s12083-025-02142-1).
   - **Use:** Blockchain-enabled quantum-secure V2I authentication comparison.

5. M. Asim, J. Wu, W. Li, Z. Lin, P. Zhang, H. He, W. Dong, and G. Mohiuddin, “Quantum-resistant blockchain architecture for secure vehicular networks: A ML-KEM-enabled approach with PoA and PoP consensus,” *Future Generation Computer Systems*, vol. 180, Art. no. 108391, 2026, doi: [10.1016/j.future.2026.108391](https://doi.org/10.1016/j.future.2026.108391).
   - **Use:** Closest current comparison for standardized ML-KEM plus vehicular blockchain, but its consensus target differs from PBFT.

6. C. I. Okafor, L. A. C. Ahakonye, D.-S. Kim, and J.-M. Lee, “ConfidSPEC-V2X: A Quantum-Blockchain Intelligence for Mitigating Confidentiality Threats in Vehicle-to-Everything Networks,” *IEEE Internet of Things Journal*, vol. 13, no. 14, 2026, doi: [10.1109/JIOT.2026.3686364](https://doi.org/10.1109/JIOT.2026.3686364).
   - **Use:** Current V2X framework combining quantum-oriented security, blockchain, and AI. Cite only for scope/context: its CV-QKD/MADRL approach is not comparable to the proposed lightweight ML-PQC design.

7. Z. Zhang, Z. Cao, and Y. Wang, “Forensics System for Internet of Vehicles Based on Post-Quantum Blockchain,” *Sensors*, vol. 25, no. 19, Art. no. 6038, 2025, doi: [10.3390/s25196038](https://doi.org/10.3390/s25196038).
   - **Use:** Recent PQ blockchain/IoV evidence and privacy context; not an AKE or PBFT baseline.

8. M. S. Mohamed, J. Godard, V. Jimenez, A. Jousse, P. P. Paños, and M. Zhang, “Post-quantum Cryptography for Connected and Cooperative Automated Mobility: A Comprehensive Overview,” in *Transport Transitions: Advancing Sustainable and Inclusive Mobility*, 2026, doi: [10.1007/978-3-032-06763-0_105](https://doi.org/10.1007/978-3-032-06763-0_105).
   - **Use:** Automotive/CCAM-specific deployment and migration context.

9. R. Alluhaibi, “Quantum resistant blockchain and deep learning revolutionize secure communications for autonomous vehicles,” *Scientific Reports*, vol. 16, Art. no. 59, 2026, doi: [10.1038/s41598-025-28938-y](https://doi.org/10.1038/s41598-025-28938-y).
   - **Use:** Contrast with heavyweight deep learning; this letter’s online logistic predictor is intentionally low-compute and must not claim an architectural ML novelty.

## Standards and security-method references (mandatory)

10. National Institute of Standards and Technology, *FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard*, Aug. 2024, doi: [10.6028/NIST.FIPS.203](https://doi.org/10.6028/NIST.FIPS.203).
    - **Use:** ML-KEM-768 definition and security framing.

11. National Institute of Standards and Technology, *FIPS 204: Module-Lattice-Based Digital Signature Standard*, Aug. 2024, doi: [10.6028/NIST.FIPS.204](https://doi.org/10.6028/NIST.FIPS.204).
    - **Use:** ML-DSA-65 definition and authenticated/non-repudiable signing claim.

12. National Institute of Standards and Technology, *Considerations for Achieving Crypto Agility: Strategies and Practices*, NIST CSWP 39, Dec. 2025, doi: [10.6028/NIST.CSWP.39](https://doi.org/10.6028/NIST.CSWP.39).
    - **Use:** Define crypto-agility precisely; do not label a one-off algorithm comparison as agility.

13. B. Blanchet, “An efficient cryptographic protocol verifier based on Prolog rules,” in *14th IEEE Computer Security Foundations Workshop*, 2001, pp. 82–96, doi: [10.1109/CSFW.2001.930138](https://doi.org/10.1109/CSFW.2001.930138).
    - **Use:** Formal-verification method citation. Clearly state that symbolic ProVerif verification does not establish implementation or side-channel security.

## Deliberately excluded from the core list

- **QSSNET** (*Vehicular Communications*, October 2026) is future-dated relative to the search cutoff; revisit it before submission if it has been formally published.
- Unreviewed preprints, vendor/blog pages, and search results without complete author/venue/DOI metadata are not suitable core references.
- Classical-only blockchain/VANET authentication is usable only for a narrow baseline or threat-model claim; it must not support a post-quantum claim.

## Citation budget for a four-page letter

Use approximately 12–18 references. The recommended minimum is [1]–[8] plus [10]–[13]. Add a classic PBFT reference and only the directly evaluated authentication baselines. Do not include every paper in this file solely because it is recent.
