# send_blender.py — minimal Direct TCP Socket sender to Blender MCP addon @ localhost:9876
# Avoids importing blmcp_client.py (which has a broken top-level RENDER_M09_CODE that crashes on import).
import socket, json, sys

HOST = "localhost"
PORT = 9876

def main():
    path = sys.argv[1]
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 300.0
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    req = json.dumps({"type": "execute", "code": code, "strict_json": False}).encode("utf-8") + b"\0"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((HOST, PORT))
        sock.sendall(req)
        buf = bytearray()
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf.extend(chunk)
            if b"\0" in buf:
                break
    line, _, _ = buf.partition(b"\0")
    print(line.decode("utf-8", errors="replace"))

if __name__ == "__main__":
    main()
