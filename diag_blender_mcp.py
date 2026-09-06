import subprocess, json, threading, time, os, sys

PY = r"C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
MCP_DIR = r"D:/d/AI/Tools/blender_mcp/mcp"

env = os.environ.copy()
env["PYTHONPATH"] = MCP_DIR + os.pathsep + env.get("PYTHONPATH", "")
env["BLENDER_PATH"] = r"D:/建模/blender/blender.exe"
env["BLENDER_MCP_HOST"] = "localhost"
env["BLENDER_MCP_PORT"] = "9876"

print(f"[diag] launching blmcp from {MCP_DIR}", flush=True)
proc = subprocess.Popen(
    [PY, "-m", "blmcp", "--transport", "stdio"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, bufsize=1, cwd=MCP_DIR, env=env,
)

def pump(label, pipe):
    try:
        for line in pipe:
            print(f"[{label}] {line}", end="", flush=True)
    except Exception as e:
        print(f"[{label}] pump error: {e}", flush=True)

threading.Thread(target=pump, args=("OUT", proc.stdout), daemon=True).start()
threading.Thread(target=pump, args=("ERR", proc.stderr), daemon=True).start()

def send(obj, wait=1.5):
    try:
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()
    except Exception as e:
        print(f"[send] error: {e}", flush=True)
    time.sleep(wait)

send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"diag","version":"1.0"}}}, wait=3.0)
send({"jsonrpc":"2.0","method":"notifications/initialized"}, wait=1.0)
print("\n>>> calling get_objects_summary ...", flush=True)
send({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_objects_summary","arguments":{}}}, wait=6.0)
time.sleep(2.0)
print("\n=== terminate ===", flush=True)
proc.terminate()
try:
    proc.wait(timeout=5)
except Exception:
    proc.kill()
print("=== done ===", flush=True)
