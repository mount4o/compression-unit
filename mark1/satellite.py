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

        server_socket.listen(5)

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}")

            with client_socket:
                received_data = b""
                compression_method = None

                # Read until we hit the null byte
                while True:
                    data = client_socket.recv(buffer_size)
                    if not data:
                        break
                    received_data += data
                    if b'\x00' in received_data:
                        received_data = received_data.rstrip(b'\x00')  # Strip null terminator
                        break
                    print(f"Received {len(received_data)} bytes of data so far")

                try:
                    # Extract the compression method
                    header_end_index = received_data.index(b'\n')
                    compression_method = received_data[:header_end_index].decode('utf-8').strip()
                    payload = received_data[header_end_index + 1:]

                    print(f"Compression method: {compression_method}")
                    print(f"Received {len(payload)} bytes of payload")

                    # Decompress the payload
                    decompressed_payload = decompress_payload(payload, compression_method)
                    print(f"Decompressed payload size: {len(decompressed_payload)} bytes")

                    # Recompress the payload
                    recompressed_payload = recompress_payload(decompressed_payload, compression_method)
                    print(f"Recompressed payload size: {len(recompressed_payload)} bytes")

                    # Calculate stats with the updated compression ratio formula
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

                    print(f"Header size: {len(packed_header)}")
                    # Send the packed header and recompressed payload, followed by a null terminator
                    client_socket.sendall(packed_header + recompressed_payload + b'\x00')

                except Exception as e:
                    error_message = f"Error processing payload: {e}"
                    print(error_message)
                    client_socket.sendall(error_message.encode('utf-8') + b'\x00')

            print(f"Connection closed from {client_address}")

if __name__ == "__main__":
    start_echo_server()
