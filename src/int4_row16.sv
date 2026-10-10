// Exact 16-term signed dot product. No activation or quantization rescale.
module hardlpu_row16_registered #(
  parameter FIXED = 1,
  parameter [63:0] WEIGHTS = 64'd0
) (
  input wire clk, rst_n, in_valid,
  input wire [127:0] x_flat,
  input wire cfg_we,
  input wire [63:0] cfg_w_flat,
  output reg out_valid,
  output reg signed [15:0] y
);
  wire [63:0] selected_weights;
  generate if (FIXED) begin : fixed_weights
    assign selected_weights = WEIGHTS;
  end else begin : programmable_weights
    reg [63:0] weights;
    always @(posedge clk) begin
      if (!rst_n) weights <= 64'd0;
      else if (cfg_we) weights <= cfg_w_flat;
    end
    assign selected_weights = weights;
  end endgenerate

  // Heap-indexed balanced tree; sign extension precedes every addition.
  wire signed [15:0] tree [0:30];
  genvar lane, node;
  generate for (lane = 0; lane < 16; lane = lane + 1) begin : terms
    wire signed [11:0] product;
    if (FIXED) begin : fixed_term
      hardlpu_synapse_fixed #(.W(WEIGHTS[4*lane+:4])) synapse
        (x_flat[8*lane+:8], product);
    end else begin : programmable_term
      hardlpu_synapse_programmable synapse
        (x_flat[8*lane+:8], selected_weights[4*lane+:4], product);
    end
    assign tree[15+lane] = {{4{product[11]}}, product};
  end
  for (node = 0; node < 15; node = node + 1) begin : reduction
    assign tree[node] = tree[2*node+1] + tree[2*node+2];
  end endgenerate

  always @(posedge clk) begin
    if (!rst_n) begin y <= 16'sd0; out_valid <= 1'b0; end
    else begin
      out_valid <= in_valid && !cfg_we;
      if (in_valid && !cfg_we) y <= tree[0];
    end
  end
endmodule
