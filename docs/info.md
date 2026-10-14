# How it works

HardLPU row16 is a digital INT8 x INT4 16-term exact INT16 reduction.
One core specializes a real Qwen3 expert weight row; the other stores16 weights
in64 flip-flops. This RTL does NOT contain an SRAM macro.
It does not execute an entire Qwen3 expert, SwiGLU, router or token generation.

Clock target:40MHz (25ns). Dedicated input/output bytes transport operands/results.
Bidirectional pins0..3 output ready,busy,weights_ready,error. Pins4..7 input
strobe/opcode. Reset or ena=0 clears protocol state; never drive output pins.

# How to test

Assert rst_n=0 for at least two rising edges, then ena=1 and rst_n=1.
Set uio_in[7:5] to opcode and pulse bit4 at a rising edge.

| Opcode | Operation |
| --- | --- |
| 1 | CLEAR |
| 2 | PUSH_X |
| 3 | EXEC_FIXED |
| 4 | EXEC_PROGRAMMABLE |
| 5 | PUSH_WEIGHTS |
| 6 | COMMIT_WEIGHTS |
| 7 | READ |

All operand/config bytes use ui_in.
Push16 signed input bytes after CLEAR. Push8 packed signed-INT4 bytes and
COMMIT before programmable execution. During busy, further strobe is rejected.
READ ui_in=0/1 returns result low/high;2 returns status;3 returns ID0xa1;
4/5 returns accepted input/config count. Status bits0..3 are ready,busy,
weights_ready,error. The protocol regression tests180645 rising-edge cycles.

Fixed weights:[1,1,2,1,0,3,3,3,1,2,0,0,3,-2,3,1]. For inputs all1, expect22.
Both cores see common operands: board supply energy cannot isolate their gains.
Measure actual board timing against the pin contract;40MHz is not silicon data.

# External hardware

Tiny Tapeout SKY130 demo board, byte IO controller/logic analyzer and a
calibrated power instrument. No physical chip has yet been tested.
The existing400x400um research GDS is NOT the official4x2 geometry.
The packaged 4x2 ECO GDS is the release candidate. Use the custom-GDS workflow;
do not substitute a fresh RTL build without requalification.

Local open-PDK checks: route/Magic DRC0, abstract macro LVS0, antenna0.
Nine RC/PVT checks at25ns: setup+2.915870294ns, hold+0.132688364ns.
Clock/IO assumptions need provider integration review. These are not full-chip
foundry signoff, measured silicon or evidence of SRAM energy superiority.
