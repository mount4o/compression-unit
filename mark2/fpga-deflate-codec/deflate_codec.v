`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: Butterfly Industries
// Engineer: Vassilen Alexandrov
//
// Create Date: 10/30/2024 17:42:30 PM
// Design Name:
// Module Name: uart_tx
// Project Name: Satellite Compression Unit
// Target Devices:
// Tool Versions:
// Description:
//
// Dependencies:
//
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
//
//////////////////////////////////////////////////////////////////////////////////

module deflate_codec (
    input clock,
    input reset,
    input transmit,
    input [7:0] sw,
    input rx,
    output tx,
    output reg [7:0] led,
    output heartbeat
);
    reg [27:0] counter;
    always @ (posedge clock) counter <= counter + 1;
    assign heartbeat = counter[27];
    //
    //  debounce the transmit push button
    //
    wire transmit_level, transmit_pulse;
    debouncer DEBOUNCE (
        .clock(clock),
        .button(transmit),
        .level(transmit_level),
        .pulse(transmit_pulse)
        );

    //
    //  instantiate uart_tx
    //
    wire active, done;
    uart_tx TX (
        .i_Clock(clock),
        .i_Clocks_per_Bit('d100),
        .i_Tx_DV(transmit_pulse),
        .i_Reset(reset),
        .i_Tx_Byte(sw),
        .o_Tx_Serial(tx),
        .o_Tx_Active(active),
        .o_Tx_Done(done)
    );
    //
    //  instantiate uart_rx
    //
    wire dv;
    wire [7:0] rx_data;
    reg [2:0] rx_done = 1'b0;
    uart_rx RX (
        .i_Clock(clock),
        .i_Clocks_per_Bit('d100),
        .i_Reset(reset),
        .i_Rx_Serial(rx),
        .o_Rx_DV(dv),
        .o_Rx_Byte(rx_data)
        );
    always @ (posedge dv) led <= rx_data;

   reg [7:0] buffer [0:1023]; // 1 KB buffer to store incoming UART data
   reg [9:0] write_ptr = 0;
   always @(posedge clock) begin
      if (dv) begin // TODO(Vassilen): Double check this, as dv is active high for 1 clock cycle
         buffer[write_ptr] <= rx_data;
         write_ptr <= write_ptr + 1;
      end
   end
endmodule
