# HardLPU row16: first Tiny Tapeout chip candidate

Digital fixed-weight INT4 specialization, with a 64-configuration-flip-flop
programmable control. **Not an actual SRAM comparison chip or a full MoE expert.**

Target: SKY130, 4x2 tiles (682.64 x 225.76um), 40MHz / 25ns.
Sixteen INT8 x INT4 products reduce to an INT16 result. Fixed weights become
constant-specialized gates and wires, not metal resistance.

## Checked evidence

- RTL and zero-delay powered-netlist regression: 180645 pin cycles each.
- Retained local precheck: 15/15, route/Magic DRC0, abstract macro LVS0, antenna0.
- Nine open-PDK RC/PVT views: worst setup +3.355ns; hold +0.002014ns.
- Approximately 2ps hold margin requires provider integration review.

This is a submission candidate, **not submitted, fabricated or tapeout-ready**.
No foundry full-chip transistor LVS, qualified PEX/SI/OCV/IR/EM/ESD, measured
silicon performance or SRAM energy superiority is claimed.

## Exact-layout CI

Run `python3 scripts/verify_release.py .` with PyYAML 6.0.2. Manually dispatch
the **gds** and **docs** Actions. GDS CI uploads the frozen ECO GDS/LEF/netlist,
runs the official precheck, and tests the hash-checked downloaded gate netlist.
Docs CI builds the provider PDF. Inspect the actual Actions results; preparing
this repository alone does not establish CI success or shuttle acceptance.

Do not replace this ECO layout with a fresh RTL synthesis and reuse its reports.
Physical changes require requalification. SPEFs are included for analysis.
The stock custom_gds metadata omits PDK revision, so the gate job pins it
explicitly. Upstream action dependencies are not entirely hermetic.

See [pin protocol](docs/info.md), [provenance](THIRD_PARTY_NOTICES.md), and
`release_manifest.json` for the exact file allowlist and SHA-256 values.
Historical evidence paths are provenance, not runtime dependencies.

## Licensing and submission boundary

Copyright 2026 eljja. The owner approved this first-chip subset for public
release and additionally licensed original materials under **Apache-2.0**.
The [parent HardLPU project](https://github.com/eljja/HardLPU) license and
unrelated files/history are unchanged. See LICENSE and NOTICE for attribution.
Provider terms, payment/order and final revision submission require separate
authorization. GitHub publication is not a fabrication order.
