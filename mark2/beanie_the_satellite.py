import streamlit as st
import zlib
import random
import math
import io
from collections import Counter
from codec import fpga_sim_deflate_compress

def compress_with_deflate(data: bytes) -> bytes:
    return zlib.compress(data)

# Read file bytes
def read_file(file) -> bytes:
    return file.read()

# Entropy calculation
def calculate_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    byte_counts = Counter(data)
    total_bytes = len(data)
    entropy = 0.0
    for count in byte_counts.values():
        p_i = count / total_bytes
        entropy -= p_i * math.log2(p_i)
    return entropy

# Random payload generation
def generate_random_payload_with_entropy(size: int, target_entropy: float) -> bytes:
    if target_entropy < 0 or target_entropy > 8:
        raise ValueError("Entropy must be between 0 and 8 bits per byte.")
    if target_entropy == 0:
        return bytes([random.randint(0, 255)] * size)
    if target_entropy == 8:
        return bytes(random.getrandbits(8) for _ in range(size))
    num_symbols = int(2 ** target_entropy)
    symbols = list(range(num_symbols))
    byte_values = random.choices(symbols, k=size)
    return bytes(byte_values)

# Display transmission information
def print_stats(payload: bytes, compressed_payload: bytes):
    original_size = len(payload)
    compressed_size = len(compressed_payload)
    st.write(f"Original size: {original_size} bytes")
    st.write(f"Compressed size: {compressed_size} bytes")
    if compressed_size < original_size:
        reduction = ((original_size - compressed_size) / original_size) * 100
        st.write(f"Compression reduced the size by {reduction:.2f}%")
    else:
        st.write("Compression did not reduce the size.")

def main():
    st.title("Beanie The Satellite")

    st.write("Beanie is lonely in space. Say something to him, send him a file or image. You can even send him some random bits with the whatever amount of entropy you desire. He probably won't understant it, though.")
    
    # Payload Type selection
    payload_type = st.radio("Select Payload Type", ['String', 'File', 'Random'])

    payload = None
    if payload_type == "String":
        payload_input = st.text_area("Enter the string to compress")
        if payload_input:
            payload = payload_input.encode('utf-8')

    elif payload_type == "File":
        file = st.file_uploader("Upload a file", type=None)
        if file:
            payload = read_file(file)

    elif payload_type == "Random":
        size = st.slider("Select the size of the random payload (in bytes)", 1, 15000, 100)
        entropy = st.slider("Select the entropy (bits per byte)", 0.0, 8.0, 4.0)
        payload = generate_random_payload_with_entropy(size, entropy)

    # Compression Algorithm selection
    if payload:
        entropy = calculate_entropy(payload)
        st.write(f"Entropy of the original payload: {entropy:.2f} bits per byte")

        st.write("Compressing with regular DEFLATE...")
        compressed_payload = compress_with_deflate(payload)
        st.write("Results for regular DEFLATE:")
        print_stats(payload, compressed_payload)
        with st.spinner("Simulating FPGA-based DEFLATE compression..."):
            fpga_compressed_payload = fpga_sim_deflate_compress(payload)
            st.write("Results for simulated FPGA-based DEFLATE:")
            print_stats(payload, fpga_compressed_payload)
        
if __name__ == "__main__":
    main()
