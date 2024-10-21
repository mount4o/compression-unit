import streamlit as st
import brotli
import gzip
import lz4.frame
import zlib
import random
import math
import bz2
import zstandard as zstd
import lzma
from PIL import Image
import io
from collections import Counter
import socket

# Compression functions
def compress_with_rle(data: bytes) -> bytes:
    """Compress data using Run-Length Encoding (RLE)."""
    if not data:
        return b""

    compressed = bytearray()
    previous_byte = data[0]
    count = 1

    for current_byte in data[1:]:
        if current_byte == previous_byte and count < 255:  # Limit run length to 255 to fit in a byte
            count += 1
        else:
            compressed.append(previous_byte)
            compressed.append(count)
            previous_byte = current_byte
            count = 1

    # Append the last byte and its count
    compressed.append(previous_byte)
    compressed.append(count)

    return bytes(compressed)

def compress_with_bzip2(data: bytes) -> bytes:
    """Compress data using Bzip2."""
    return bz2.compress(data)

def compress_with_zstd(data: bytes) -> bytes:
    """Compress data using Zstandard."""
    cctx = zstd.ZstdCompressor()
    return cctx.compress(data)

def compress_with_lzma(data: bytes) -> bytes:
    """Compress data using LZMA."""
    return lzma.compress(data)

def compress_with_brotli(data: bytes) -> bytes:
    return brotli.compress(data)

def compress_with_gzip(data: bytes) -> bytes:
    return gzip.compress(data)

def compress_with_lz4(data: bytes) -> bytes:
    return lz4.frame.compress(data)

def compress_with_deflate(data: bytes) -> bytes:
    return zlib.compress(data)

def compress_image_lossless(image_path: bytes) -> bytes:
    """Compress an image using lossless JPEG compression."""
    with Image.open(io.BytesIO(image_path)) as img:
        if img.mode != 'RGB':
            img = img.convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=100, optimize=True)
        return buffer.getvalue()

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
def simulate_transmission(payload: bytes, compressed_payload: bytes):
    original_size = len(payload)
    compressed_size = len(compressed_payload)
    st.write(f"Original size: {original_size} bytes")
    st.write(f"Compressed size: {compressed_size} bytes")
    if compressed_size < original_size:
        reduction = ((original_size - compressed_size) / original_size) * 100
        st.write(f"Compression reduced the size by {reduction:.2f}%")
    else:
        st.write("Compression did not reduce the size.")

# Function to send payload to the echo server and receive it back
def send_payload_to_server(payload: bytes, compression_method: str) -> None:
    server_ip = '127.0.0.1'  # Assuming echo server is running locally
    server_port = 122        # Echo server port

    try:
        # Create a socket object
        sock_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_fd.settimeout(5)  # Set a timeout of 5 seconds
        st.write(f"Connecting to {server_ip} on port {server_port}...")

        # Connect to the server
        sock_fd.connect((server_ip, server_port))
        st.write(f"Connected to {server_ip} on port {server_port}")

        # Send the compression method first, followed by the payload
        st.write(f"Sending {compression_method} compressed payload (size: {len(payload)} bytes)...")
        sock_fd.sendall(f"{compression_method}\n".encode('utf-8') + payload + b'\n')

        st.write("Payload sent. Awaiting stats and recompressed payload...")


        buffer_size = 1024
        if (len(payload) < buffer_size):
            buffer_size = len(payload)
        
        # Receive the response (stats + recompressed payload)
        received_data = b""
        while True:
            try:
                data = sock_fd.recv(buffer_size)  # Receive in chunks
                if not data:
                    break  # No more data
                received_data += data
            except socket.timeout:
                st.write("Timeout while waiting for server response")
                break

        # Separate stats from the recompressed payload
        try:
            if b'\n\n' in received_data:
                response_parts = received_data.split(b'\n\n', 1)
                stats_message = response_parts[0].decode('utf-8')
                recompressed_payload = response_parts[1]

                # Display the stats
                st.write("Stats received from satellite:")
                st.write(stats_message)
            else:
                # If the expected separator is not found, handle it
                st.write("Invalid response format from server")
                st.write(received_data.decode('utf-8'))

        except Exception as e:
            st.write(f"Error processing the response: {e}")

    except socket.error as e:
        st.write(f"Socket error: {e}")
    finally:
        sock_fd.close()

# Updated main function
def main():
    st.title("Payload Compression Simulation")

    # Payload Type selection
    payload_type = st.radio("Select Payload Type", ['String', 'File', 'Image', 'Random'])

    payload = None
    if payload_type == "String":
        payload_input = st.text_area("Enter the string to compress")
        if payload_input:
            payload = payload_input.encode('utf-8')

    elif payload_type == "File":
        file = st.file_uploader("Upload a file", type=None)
        if file:
            payload = read_file(file)

    elif payload_type == "Image":
        image_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg", "dng", "raw", "nef", "cr2", "arw"])
        if image_file:
            payload = read_file(image_file)

            if image_file.type in ['image/dng', 'image/x-adobe-dng', 'image/raw', 'image/x-raw', 'image/nef', 'image/x-canon-cr2', 'image/arw']:
                st.write("RAW image detected, processing as binary data.")
                compressed_payload = payload  # Can apply general compression later
            else:
                compressed_payload = compress_image_lossless(payload)
                st.write("Lossless compression applied to image.")

            simulate_transmission(payload, compressed_payload)
            send_payload_to_server(compressed_payload, compression_method)  # Send to server
            return

    elif payload_type == "Random":
        size = st.slider("Select the size of the random payload (in bytes)", 1, 100000, 1024)
        entropy = st.slider("Select the entropy (bits per byte)", 0.0, 8.0, 4.0)
        payload = generate_random_payload_with_entropy(size, entropy)

    # Compression Algorithm selection
    if payload:
        compression_method = st.selectbox("Choose a compression method", ['brotli', 'gzip', 'lz4', 'deflate', 'rle', 'bzip2', 'zstd', 'lzma'])

        entropy = calculate_entropy(payload)
        st.write(f"Entropy of the original payload: {entropy:.2f} bits per byte")

        if compression_method == "brotli":
            compressed_payload = compress_with_brotli(payload)
        elif compression_method == "gzip":
            compressed_payload = compress_with_gzip(payload)
        elif compression_method == "lz4":
            compressed_payload = compress_with_lz4(payload)
        elif compression_method == "deflate":
            compressed_payload = compress_with_deflate(payload)
        elif compression_method == "rle":
            compressed_payload = compress_with_rle(payload)
        elif compression_method == "bzip2":
            compressed_payload = compress_with_bzip2(payload)
        elif compression_method == "zstd":
            compressed_payload = compress_with_zstd(payload)
        elif compression_method == "lzma":
            compressed_payload = compress_with_lzma(payload)

        simulate_transmission(payload, compressed_payload)
        send_payload_to_server(compressed_payload, compression_method)  # Send the compressed payload to server

if __name__ == "__main__":
    main()
