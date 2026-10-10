`default_nettype none
// Byte-wide, single-clock test access. Arithmetic is the frozen row16 core.
// uio[7:5] command, uio[4] strobe; uio[3:0] are output-only status.
module tt_um_hardlpu_row16 (
  input wire [7:0] ui_in,
  output reg [7:0] uo_out,
  input wire [7:0] uio_in,
  output wire [7:0] uio_out,
  output wire [7:0] uio_oe,
  input wire ena, clk, rst_n
);
  localparam [63:0] FIXTURE = 64'h13e3002133301211;
  reg [127:0] inputs;
  reg [63:0] configuration;
  reg [4:0] input_count;
  reg [3:0] configuration_count;
  reg weights_ready, busy, result_ready, error, pending_programmable;
  reg [15:0] result;
  wire selected_reset_n = rst_n && ena;
  wire request = ena && rst_n && uio_in[4];
  wire [2:0] command = uio_in[7:5];
  wire execute_fixed = request && !busy && command == 3 && input_count == 16;
  wire execute_programmable = request && !busy && command == 4 && input_count == 16 && weights_ready;
  wire configure = request && !busy && command == 6 && configuration_count == 8;
  wire [15:0] fixed_y, programmable_y;
  wire fixed_valid, programmable_valid;
  wire [3:0] status = {error, weights_ready, busy, result_ready};
  assign uio_out = {4'b0000, status};
  assign uio_oe = ena ? 8'h0f : 8'h00;

  hardlpu_row16_registered #(.FIXED(1), .WEIGHTS(FIXTURE)) fixed_core
    (.clk(clk), .rst_n(selected_reset_n), .in_valid(execute_fixed),
     .x_flat(inputs), .cfg_we(1'b0), .cfg_w_flat(64'b0),
     .out_valid(fixed_valid), .y(fixed_y));
  hardlpu_row16_registered #(.FIXED(0)) programmable_core
    (.clk(clk), .rst_n(selected_reset_n), .in_valid(execute_programmable),
     .x_flat(inputs), .cfg_we(configure), .cfg_w_flat(configuration),
     .out_valid(programmable_valid), .y(programmable_y));

  // A command is accepted on each selected rising edge with strobe high.
  // Execute consumes one edge; the next edge captures the core result.
  always @(posedge clk) begin
    if (!selected_reset_n) begin
      inputs <= 0;
      configuration <= 0;
      input_count <= 0;
      configuration_count <= 0;
      weights_ready <= 0;
      busy <= 0;
      result_ready <= 0;
      error <= 0;
      pending_programmable <= 0;
      result <= 0;
      uo_out <= 0;
    end else if (busy) begin
      busy <= 0;
      if ((pending_programmable && programmable_valid) ||
          (!pending_programmable && fixed_valid)) begin
        result <= pending_programmable ? programmable_y : fixed_y;
        result_ready <= 1;
      end else begin
        result_ready <= 0;
        error <= 1;
      end
      if (request) error <= 1;
    end else if (request) begin
      case (command)
        0: begin end
        1: begin
          input_count <= 0;
          configuration_count <= 0;
          result_ready <= 0;
          error <= 0;
          uo_out <= 0;
        end
        2: begin
          if (input_count < 16) begin
            // Lane zero is sent first; sixteen shifts overwrite the whole word.
            inputs <= {ui_in, inputs[127:8]};
            input_count <= input_count + 1'b1;
            result_ready <= 0;
          end else error <= 1;
        end
        3, 4: begin
          if (execute_fixed || execute_programmable) begin
            busy <= 1;
            pending_programmable <= execute_programmable;
            result_ready <= 0;
          end else error <= 1;
        end
        5: begin
          if (configuration_count < 8) begin
            configuration <= {ui_in, configuration[63:8]};
            configuration_count <= configuration_count + 1'b1;
          end else error <= 1;
        end
        6: begin
          if (configure) begin
            weights_ready <= 1;
            configuration_count <= 0;
            result_ready <= 0;
          end else error <= 1;
        end
        7: begin
          case (ui_in)
            0: if (result_ready) uo_out <= result[7:0]; else error <= 1;
            1: if (result_ready) uo_out <= result[15:8]; else error <= 1;
            2: uo_out <= {4'b0, status};
            3: uo_out <= 8'ha1;
            4: uo_out <= {3'b0, input_count};
            5: uo_out <= {4'b0, configuration_count};
            default: error <= 1;
          endcase
        end
      endcase
    end
  end
endmodule
`default_nettype wire
