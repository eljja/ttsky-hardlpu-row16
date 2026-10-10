`timescale 1ns/1ps
module tb_chip;
reg clk=0; always #10 clk=~clk;
reg rst_n=0,ena=0; reg [7:0] ui_in=0,uio_in=0;
wire [7:0] uo_out,uio_out,uio_oe;
`ifdef GATE
supply1 VPWR; supply0 VGND;
`endif
tt_um_hardlpu_row16 dut(.clk(clk),.rst_n(rst_n),.ena(ena),.ui_in(ui_in),.uio_in(uio_in),
.uo_out(uo_out),.uio_out(uio_out),.uio_oe(uio_oe)
`ifdef GATE
,.VPWR(VPWR),.VGND(VGND)
`endif
);
reg [39:0] vectors[0:180644]; integer i;
initial begin
 $readmemh("protocol.mem",vectors);
 for(i=0;i<180645;i=i+1) begin
  @(negedge clk);
  ui_in=vectors[i][7:0];uio_in=vectors[i][15:8];rst_n=vectors[i][16];ena=vectors[i][17];
  @(posedge clk); #1;
  if(uo_out!==vectors[i][25:18] || uio_out!=={4'b0,vectors[i][29:26]} || uio_oe!==vectors[i][37:30])
   $fatal(1,"PIN_MISMATCH cycle=%0d data=%h/%h status=%h/%h oe=%h/%h",i,
    uo_out,vectors[i][25:18],uio_out,vectors[i][29:26],uio_oe,vectors[i][37:30]);
 end
 $display("CHIP_ACCESS cycles=180645 pass=180645"); $finish;
end
endmodule
