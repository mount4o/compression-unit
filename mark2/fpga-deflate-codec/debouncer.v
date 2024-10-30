`timescale 1ns / 1ps
module debouncer(
    input clock,        // assume 100MHz
    input button,       // button that was pushed
    output reg level,   // debounced output level, up as long as button is pushed
    output pulse    // one-shot of the level, 2 clock ticks long
    );

    //
    //  register the input button click with the system clock.
    //
    reg ff1 = 0, ff2 = 0;
    always @ (posedge clock) begin
        ff1 <= button;
        ff2 <= ff1;
    end
    //
    //  when the input button is pushed or released, we increment or
    //  decrement a counter.   the counter has to reach a threshold
    //  before we decide that the push-button state has chnaged.
    //
    //  let's assume we have to have the button pushed for 1ms
    //  that's 100,000 clock ticks, so we will need at least 17 bits

    reg [16:0] count = 0;
    always @ (posedge clock) begin
        if (ff2) begin
            if (~&count) count <= count + 1;
        end
        else begin
            if (|count) count <= count - 1;
        end
        if (count > 'd100000) level <= 1;
        else level <= 0;
    end

    reg dff1 = 0, dff2 = 0;
    always @ (posedge clock) begin
            dff1 <= level;
            dff2 <= dff1;
    end
    assign pulse = level & ~dff2;

endmodule
