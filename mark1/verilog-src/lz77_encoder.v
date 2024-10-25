module lz77_encoder #(
    parameter DATA_WIDTH = 8,           // Width of input data (8-bit ASCII)
    parameter WINDOW_SIZE = 16,         // Sliding window size (4-bit offset for simplicity)
    parameter MAX_MATCH_LEN = 4         // Maximum match length
)(
    input wire clk,                     // Clock signal
    input wire reset,                   // Reset signal
    input wire [DATA_WIDTH-1:0] data_in,  // Input data (one symbol at a time)
    input wire data_valid,              // Signal to indicate valid input data
    output reg [DATA_WIDTH-1:0] literal,  // Literal output (if no match)
    output reg [3:0] match_offset,      // Back-reference offset (4-bit)
    output reg [3:0] match_length,      // Match length (4-bit)
    output reg literal_valid,           // Output flag for literal
    output reg match_valid              // Output flag for back-reference
);

    // Sliding window buffer to store the previous WINDOW_SIZE symbols
    reg [DATA_WIDTH-1:0] window [0:WINDOW_SIZE-1]; // Sliding window memory
    reg [3:0] write_ptr; // Write pointer for the sliding window (cyclic buffer)

    // Internal signals
    integer i;                     // Loop counter for match search
    reg [3:0] best_offset_reg, best_offset_comb;  // Best offset found
    reg [3:0] best_length_reg, best_length_comb;  // Best match length found
    reg [3:0] match_len; // Match length in the loop

    // State machine states (Verilog-2005 compatible)
    localparam IDLE = 2'b00;
    localparam SEARCH = 2'b01;
    localparam OUTPUT_MATCH = 2'b10;
    localparam OUTPUT_LITERAL = 2'b11;

    reg [1:0] state, next_state;

    // Write data to the sliding window buffer (cyclically)
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            write_ptr <= 0;
            for (i = 0; i < WINDOW_SIZE; i = i + 1) begin
                window[i] = 0;   // Use blocking assignment for reset
            end
        end else if (data_valid) begin
            window[write_ptr] <= data_in; // Non-blocking assignment for regular operation
            write_ptr <= (write_ptr + 1) % WINDOW_SIZE[3:0]; // Update cyclic pointer with proper width
        end
    end

    // FSM to manage compression stages
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            state <= IDLE;
            best_length_reg <= 0;
            best_offset_reg <= 0;
        end else begin
            state <= next_state;
            best_length_reg <= best_length_comb;   // Non-blocking assignment for match length
            best_offset_reg <= best_offset_comb;   // Non-blocking assignment for offset
        end
    end

    // Match search in a combinational block to avoid the delay inside for loops
    always @(*) begin
        // Default values for combinational outputs to avoid latch inference
        next_state = state;
        literal_valid = 0;
        match_valid = 0;
        literal = 0;
        match_offset = 0;
        match_length = 0;
        best_length_comb = 0;
        best_offset_comb = 0;
        match_len = 0;  // Set default value for match_len to avoid latches

        case (state)
            IDLE: begin
                if (data_valid) begin
                    // Start searching for a match in the sliding window
                    next_state = SEARCH;
                end
            end

            SEARCH: begin
                // Combinational search through the sliding window to find the longest match
                for (i = 0; i < WINDOW_SIZE; i = i + 1) begin
                    if (window[i] == data_in) begin
                        // Potential match found; check further characters
                        match_len = 1;
                        while (match_len < MAX_MATCH_LEN &&
                               window[((i + match_len) % WINDOW_SIZE[3:0])] == data_in) begin
                            match_len = match_len + 1;
                        end

                        // If this match is the best so far, update best_offset and best_length
                        if (match_len > best_length_comb) begin
                            best_length_comb = match_len;
                            best_offset_comb = (write_ptr - i) % WINDOW_SIZE[3:0]; // Cast to 4 bits
                        end
                    end
                end

                // Check if a match was found
                if (best_length_comb > 1) begin
                    // Output the back-reference if a match was found
                    match_offset = best_offset_reg;  // Output the registered offset
                    match_length = best_length_reg;  // Output the registered length
                    match_valid = 1;
                    next_state = OUTPUT_MATCH;
                end else begin
                    // If no match, output the literal value
                    literal = data_in;
                    literal_valid = 1;
                    next_state = OUTPUT_LITERAL;
                end
            end

            OUTPUT_MATCH: begin
                // After outputting the match, go back to IDLE
                next_state = IDLE;
            end

            OUTPUT_LITERAL: begin
                // After outputting the literal, go back to IDLE
                next_state = IDLE;
            end

            default: next_state = IDLE;
        endcase
    end

endmodule
