// Exact signed arithmetic units, independent of the expert activation contract.
module hardlpu_synapse_fixed #(parameter signed [3:0] W = 4'sd1)
  (input wire signed [7:0] x, output wire signed [11:0] p);
  wire signed [11:0] sx = {{4{x[7]}}, x};
  // Two's-complement INT4: W = b0 + 2*b1 + 4*b2 - 8*b3.
  assign p = (W[0] ? sx : 12'sd0) + (W[1] ? (sx <<< 1) : 12'sd0)
           + (W[2] ? (sx <<< 2) : 12'sd0) - (W[3] ? (sx <<< 3) : 12'sd0);
endmodule

module hardlpu_synapse_programmable
  (input wire signed [7:0] x, input wire signed [3:0] w,
   output wire signed [11:0] p);
  assign p = x * w;
endmodule

module hardlpu_dot4_registered #(
  parameter FIXED = 1,
  parameter signed [3:0] W0 = 1, W1 = -2, W2 = 3, W3 = -4
) (
  input wire clk, rst_n, in_valid,
  input wire [31:0] x_flat,
  input wire cfg_we, input wire [15:0] cfg_w_flat,
  output reg out_valid, output reg signed [13:0] y
);
  wire signed [11:0] p0, p1, p2, p3;
  generate if (FIXED) begin : fixed_terms
    hardlpu_synapse_fixed #(.W(W0)) s0(x_flat[0+:8], p0);
    hardlpu_synapse_fixed #(.W(W1)) s1(x_flat[8+:8], p1);
    hardlpu_synapse_fixed #(.W(W2)) s2(x_flat[16+:8], p2);
    hardlpu_synapse_fixed #(.W(W3)) s3(x_flat[24+:8], p3);
  end else begin : programmable_terms
    reg [15:0] weights;
    always @(posedge clk) begin
      if (!rst_n) weights <= 16'd0;
      else if (cfg_we) weights <= cfg_w_flat;
    end
    hardlpu_synapse_programmable s0(x_flat[0+:8], weights[0+:4], p0);
    hardlpu_synapse_programmable s1(x_flat[8+:8], weights[4+:4], p1);
    hardlpu_synapse_programmable s2(x_flat[16+:8], weights[8+:4], p2);
    hardlpu_synapse_programmable s3(x_flat[24+:8], weights[12+:4], p3);
  end endgenerate
  wire signed [13:0] sum = {{2{p0[11]}},p0} + {{2{p1[11]}},p1}
                          + {{2{p2[11]}},p2} + {{2{p3[11]}},p3};
  always @(posedge clk) begin
    if (!rst_n) begin y <= 14'sd0; out_valid <= 1'b0; end
    else begin
      out_valid <= in_valid && !cfg_we;
      if (in_valid && !cfg_we) y <= sum;
    end
  end
endmodule
