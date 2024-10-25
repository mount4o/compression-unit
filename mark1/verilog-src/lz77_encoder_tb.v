module tb_lz77_encoder;
    reg clk;
    reg reset;
    reg [7:0] data_in;
    reg data_valid;
    wire [7:0] literal;
    wire [3:0] match_offset;
    wire [3:0] match_length;
    wire literal_valid;
    wire match_valid;

    // Instantiate the LZ77 encoder
    lz77_encoder #(
        .DATA_WIDTH(8),
        .WINDOW_SIZE(16),
        .MAX_MATCH_LEN(4)
    ) uut (
        .clk(clk),
        .reset(reset),
        .data_in(data_in),
        .data_valid(data_valid),
        .literal(literal),
        .match_offset(match_offset),
        .match_length(match_length),
        .literal_valid(literal_valid),
        .match_valid(match_valid)
    );

    // Generate clock
    always #5 clk = ~clk;

    initial begin
        // Initialize inputs
        clk = 0;
        reset = 1;
        data_in = 0;
        data_valid = 0;
        #10 reset = 0;

        // Apply input data (e.g., ABCABCABC)
        #10 data_in = "A"; data_valid = 1;
        #10 data_in = "B"; data_valid = 1;
        #10 data_in = "C"; data_valid = 1;
        #10 data_in = "A"; data_valid = 1;
        #10 data_in = "B"; data_valid = 1;
        #10 data_in = "C"; data_valid = 1;
        #10 data_in = "A"; data_valid = 1;
        #10 data_in = "B"; data_valid = 1;
        #10 data_in = "C"; data_valid = 1;
        #10 data_valid = 0;

        #100;
        $finish;
    end

    // Monitor outputs
    initial begin
        $monitor("Time: %0t | Literal: %h, Match Offset: %d, Match Length: %d, Literal Valid: %b, Match Valid: %b",
                 $time, literal, match_offset, match_length, literal_valid, match_valid);
    end
endmodule
