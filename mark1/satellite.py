import socket
import zlib
import lzma
import brotli
import lz4.frame
import zstandard as zstd
import bz2
import struct
from PIL import Image
import io

# Compression with RLE (Run-Length Encoding)
def compress_with_rle(data: bytes) -> bytes:
    if not data:
        return b""
    compressed = bytearray()
    previous_byte = data[0]
    count = 1
    for current_byte in data[1:]:
        if current_byte == previous_byte and count < 255:
            count += 1
        else:
            compressed.append(previous_byte)
            compressed.append(count)
            previous_byte = current_byte
            count = 1
    compressed.append(previous_byte)
    compressed.append(count)
    return bytes(compressed)

def decompress_with_rle(data: bytes) -> bytes:
    decompressed = bytearray()
    i = 0
    while i < len(data):
        byte = data[i]
        count = data[i + 1]
        decompressed.extend([byte] * count)
        i += 2
    return bytes(decompressed)

def compress_with_deflate(data: bytes) -> bytes:
    """Compress data using DEFLATE (zlib)."""
    return zlib.compress(data)

# Decompression for bzip2, zstd, lzma, brotli, lz4, deflate
def decompress_payload(payload: bytes, compression_method: str) -> bytes:
    try:
        if compression_method == "deflate":
            return zlib.decompress(payload)
        elif compression_method == "lzma":
            return lzma.decompress(payload)
        elif compression_method == "brotli":
            return brotli.decompress(payload)
        elif compression_method == "lz4":
            return lz4.frame.decompress(payload)
        elif compression_method == "zstd":
            dctx = zstd.ZstdDecompressor()
            return dctx.decompress(payload)
        elif compression_method == "bzip2":
            return bz2.decompress(payload)
        elif compression_method == "rle":
            return decompress_with_rle(payload)
        elif compression_method == "lossless_image":
            return compress_image_lossless(payload)  # In this case, it's recompression
        else:
            raise ValueError(f"Unknown compression method: {compression_method}")
    except Exception as e:
        raise RuntimeError(f"Decompression failed: {e}")

# Compression functions (mirrors decompression)
def recompress_payload(payload: bytes, compression_method: str) -> bytes:
    try:
        if compression_method == "deflate":
            return zlib.compress(payload)
        elif compression_method == "lzma":
            return lzma.compress(payload)
        elif compression_method == "brotli":
            return brotli.compress(payload)
        elif compression_method == "lz4":
            return lz4.frame.compress(payload)
        elif compression_method == "zstd":
            cctx = zstd.ZstdCompressor()
            return cctx.compress(payload)
        elif compression_method == "bzip2":
            return bz2.compress(payload)
        elif compression_method == "rle":
            return compress_with_rle(payload)
        elif compression_method == "lossless_image":
            return compress_image_lossless(payload)  # Image is compressed in lossless JPEG
        else:
            raise ValueError(f"Unknown compression method: {compression_method}")
    except Exception as e:
        raise RuntimeError(f"Recompression failed: {e}")

def start_echo_server():
    server_ip = '0.0.0.0'  # Listen on all available interfaces
    server_port = 1222      # Updated port to 1222
    buffer_size = 1024      # Size of the chunks to read from clients

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((server_ip, server_port))
        print(f"Server listening on {server_ip}:{server_port}")

        server_socket.listen(15)

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}")

            with client_socket:
                try:
                    # Step 1: Read the 4-byte preamble
                    preamble = client_socket.recv(4)
                    if preamble != b'\xaa\xbb\xcc\xdd':
                        raise ValueError("Invalid preamble received.")
                    print("Preamble received and validated.")

                    # Step 2: Read the 4-byte payload size header
                    size_header = client_socket.recv(4)
                    if len(size_header) != 4:
                        raise ValueError("Incomplete size header received.")
                    payload_size = struct.unpack("!I", size_header)[0]
                    print(f"Payload size received: {payload_size} bytes")

                    # Step 3: Read the compression method (up to the first newline character)
                    compression_method = b""
                    while True:
                        byte = client_socket.recv(1)
                        if byte == b'\n':
                            break
                        compression_method += byte
                    compression_method = compression_method.decode('utf-8').strip()
                    print(f"Compression method: {compression_method}")

                    # Step 4: Read the payload based on the payload size
                    payload = b""
                    while len(payload) < payload_size:
                        chunk = client_socket.recv(min(buffer_size, payload_size - len(payload)))
                        if not chunk:
                            raise ConnectionError("Connection closed unexpectedly.")
                        payload += chunk
                    print(f"Received payload of size: {len(payload)} bytes")

                    # Process the payload (decompress, recompress, etc.)
                    decompressed_payload = decompress_payload(payload, compression_method)
                    print(f"Decompressed payload size: {len(decompressed_payload)} bytes")

                    recompressed_payload = recompress_payload(decompressed_payload, compression_method)
                    print(f"Recompressed payload size: {len(recompressed_payload)} bytes")

                    # Calculate statistics
                    original_size = len(payload)
                    decompressed_size = len(decompressed_payload)
                    recompressed_size = len(recompressed_payload)
                    compression_ratio = ((decompressed_size - recompressed_size) / decompressed_size) * 100

                    # Pack the stats header using struct.pack
                    header_format = "iii f"
                    packed_header = struct.pack(
                        header_format,
                        original_size,
                        decompressed_size,
                        recompressed_size,
                        compression_ratio
                    )

                    # Send the packed header and recompressed payload to the client
                    client_socket.sendall(packed_header + recompressed_payload)
                    print("Response sent to client.")

                except Exception as e:
                    error_message = f"Error processing payload: {e}"
                    print(error_message)
                    client_socket.sendall(error_message.encode('utf-8') + b'\x00')

            print(f"Connection closed from {client_address}")

if __name__ == "__main__":
    start_echo_server()
