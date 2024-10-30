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

//////////////////////////////////////////////////////////////////////
// File Downloaded from http://www.nandland.com
//////////////////////////////////////////////////////////////////////
// This file contains the UART Transmitter.  This transmitter is able
// to transmit 8 bits of serial data, one start bit, one stop bit,
// and no parity bit.  When transmit is complete o_Tx_done will be
// driven high for one clock cycle.
//
// input i_Clocks_per_Bit = (Frequency of i_Clock)/(Frequency of UART)
// Example: 100 MHz Clock, 1MHz baud UART
// i_Clocks_per_Bit = (100,000,000)/(1,000,000) = 100
//
// when input i_Tx_DV goes high, data i_Tx_Byte is latched and transmitted
// when transmission is done, o_Tx_Done is asserted for 1 or 2 clock cycles
//
module uart_tx (
   input       i_Clock,
   input [15:0] i_Clocks_per_Bit,
   input       i_Reset,
   input       i_Tx_DV,
   input [7:0] i_Tx_Byte,
   output      o_Tx_Active,
   output reg  o_Tx_Serial,
   output      o_Tx_Done,
   output [7:0] o_debug
   );

  localparam s_IDLE         = 3'b000;
  localparam s_TX_START_BIT = 3'b001;
  localparam s_TX_DATA_BITS = 3'b010;
  localparam s_TX_STOP_BIT  = 3'b011;
  localparam s_CLEANUP      = 3'b100;

  reg [2:0]    r_SM_Main     = 0; // State machine
  reg [11:0]   r_Clock_Count = 0;
  reg [2:0]    r_Bit_Index   = 0; // which of 8 max data bits
  reg [7:0]    r_Tx_Data     = 0;
  reg          r_Tx_Done     = 0;
  reg          r_Tx_Active   = 0;

  assign o_debug = {i_Clock,i_Tx_DV,o_Tx_Active,o_Tx_Done,o_Tx_Serial,r_SM_Main};
  always @(posedge i_Clock or posedge i_Reset)
    if (i_Reset) r_SM_Main <= s_IDLE;
    else begin

      case (r_SM_Main)
        s_IDLE :
          begin
            o_Tx_Serial   <= 1'b1;         // Drive Line High for Idle
            r_Tx_Done     <= 1'b0;
            r_Clock_Count <= 0;
            r_Bit_Index   <= 0;

            if (i_Tx_DV == 1'b1)
              begin
                r_Tx_Active <= 1'b1;
                r_Tx_Data   <= i_Tx_Byte;
                r_SM_Main   <= s_TX_START_BIT;
              end
            else
              r_SM_Main <= s_IDLE;
          end // case: s_IDLE

        // Send out Start Bit. Start bit = 0
        s_TX_START_BIT :
          begin
            o_Tx_Serial <= 1'b0;

            // Wait i_Clocks_per_Bit-1 clock cycles for start bit to finish
            if (r_Clock_Count < i_Clocks_per_Bit-1)
              begin
                r_Clock_Count <= r_Clock_Count + 1;
                r_SM_Main     <= s_TX_START_BIT;
              end
            else
              begin
                r_Clock_Count <= 0;
                r_SM_Main     <= s_TX_DATA_BITS;
              end
          end // case: s_TX_START_BIT


        // Wait i_Clocks_per_Bit-1 clock cycles for data bits to finish
        s_TX_DATA_BITS :
          begin
            o_Tx_Serial <= r_Tx_Data[r_Bit_Index];

            if (r_Clock_Count < i_Clocks_per_Bit-1)
              begin
                r_Clock_Count <= r_Clock_Count + 1;
                r_SM_Main     <= s_TX_DATA_BITS;
              end
            else
              begin
                r_Clock_Count <= 0;

                // Check if we have sent out all bits
                if (r_Bit_Index < 7)
                  begin
                    r_Bit_Index <= r_Bit_Index + 1;
                    r_SM_Main   <= s_TX_DATA_BITS;
                  end
                else
                  begin
                    r_Bit_Index <= 0;
                    r_SM_Main   <= s_TX_STOP_BIT;
                  end
              end
          end // case: s_TX_DATA_BITS


        // Send out Stop bit.  Stop bit = 1
        s_TX_STOP_BIT :
          begin
            o_Tx_Serial <= 1'b1;

            // Wait i_Clocks_per_Bit-1 clock cycles for Stop bit to finish
            if (r_Clock_Count < i_Clocks_per_Bit-1)
              begin
                r_Clock_Count <= r_Clock_Count + 1;
                r_SM_Main     <= s_TX_STOP_BIT;
              end
            else
              begin
                r_Tx_Done     <= 1'b1;
                r_Clock_Count <= 0;
                r_SM_Main     <= s_CLEANUP;
                r_Tx_Active   <= 1'b0;
              end
          end // case: s_Tx_STOP_BIT


        // Stay here 1 clock
        s_CLEANUP :
          begin
            r_Tx_Done <= 1'b1;
            r_SM_Main <= s_IDLE;
          end


        default :
          r_SM_Main <= s_IDLE;

      endcase
    end

  assign o_Tx_Active = r_Tx_Active;
  assign o_Tx_Done   = r_Tx_Done;

endmodule
