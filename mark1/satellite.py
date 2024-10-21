import socket
import gzip
import zlib
import lzma
import brotli
import lz4.frame
import zstandard as zstd
import bz2

# Function to decompress the payload
def decompress_payload(payload: bytes, compression_method: str) -> bytes:
    try:
        if compression_method == "gzip":
            return gzip.decompress(payload)
        elif compression_method == "zlib":
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
        else:
            raise ValueError(f"Unknown compression method: {compression_method}")
    except Exception as e:
        raise RuntimeError(f"Decompression failed: {e}")

# Function to recompress the payload using the same compression method
def recompress_payload(payload: bytes, compression_method: str) -> bytes:
    try:
        if compression_method == "gzip":
            return gzip.compress(payload)
        elif compression_method == "zlib":
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
        else:
            raise ValueError(f"Unknown compression method: {compression_method}")
    except Exception as e:
        raise RuntimeError(f"Recompression failed: {e}")

def start_echo_server():
    server_ip = '0.0.0.0'  # Listen on all available interfaces (localhost and external)
    server_port = 122      # Port to listen on
    buffer_size = 1024     # Size of the chunks to read from clients

    # Create a TCP/IP socket
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

                while True:
                    data = client_socket.recv(buffer_size)

def start_echo_server():
    server_ip = '0.0.0.0'
    server_port = 122
    buffer_size = 1024

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

                while True:
                    data = client_socket.recv(buffer_size)
                    if not data:
                        break
                    received_data += data

                try:
                    header_end_index = received_data.index(b'\n')
                    compression_method = received_data[:header_end_index].decode('utf-8').strip()
                    payload = received_data[header_end_index + 1:]

                    print(f"Compression method: {compression_method}")
                    print(f"Received {len(payload)} bytes of payload")

                    # Strip any additional newlines from the payload
                    payload = payload.rstrip(b'\n')

                    # Decompress the payload
                    decompressed_payload = decompress_payload(payload, compression_method)
                    print(f"Decompressed payload size: {len(decompressed_payload)} bytes")

                    # Recompress the payload
                    recompressed_payload = recompress_payload(decompressed_payload, compression_method)
                    print(f"Recompressed payload size: {len(recompressed_payload)} bytes")

                    # Calculate stats
                    original_size = len(payload)
                    decompressed_size = len(decompressed_payload)
                    recompressed_size = len(recompressed_payload)
                    compression_ratio = (original_size / decompressed_size) * 100

                    # Create a stats response
                    stats_message = (
                        f"Original size: {original_size} bytes\n"
                        f"Decompressed size: {decompressed_size} bytes\n"
                        f"Recompressed size: {recompressed_size} bytes\n"
                        f"Compression ratio: {compression_ratio:.2f}%\n"
                    )
                    print(stats_message)

                    # Send the recompressed payload and stats back to the client, with \n\n as the separator
                    response = stats_message.encode('utf-8') + b'\n\n' + recompressed_payload
                    print(f"Sending response to client:\n{stats_message}\n(recompressed payload size: {len(recompressed_payload)} bytes)")
                    client_socket.sendall(response)

                except Exception as e:
                    error_message = f"Error processing payload: {e}"
                    print(error_message)
                    client_socket.sendall(error_message.encode('utf-8'))

            print(f"Connection closed from {client_address}")

if __name__ == "__main__":
    start_echo_server()
