#!/usr/bin/env python3
import subprocess
import threading
import sys
import signal

# ANSI Color Codes
COLORS = {
    "ragmate-control-plane": "\033[94m",  # Blue
    "ragmate-ai-engine": "\033[92m",      # Green
    "ragmate-nginx": "\033[93m",          # Yellow
    "ragmate-redis": "\033[95m",          # Magenta
    "RESET": "\033[0m"
}

containers = [
    "ragmate-control-plane",
    "ragmate-ai-engine",
    "ragmate-nginx",
    "ragmate-redis"
]

processes = []

def stream_log(container_name):
    color = COLORS.get(container_name, COLORS["RESET"])
    prefix = f"{color}[{container_name}]{COLORS['RESET']} "
    
    # Start docker logs process
    cmd = ["docker", "logs", "-f", container_name]
    try:
        proc = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            bufsize=1
        )
        processes.append(proc)
        
        # Read logs line by line
        for line in iter(proc.stdout.readline, ""):
            sys.stdout.write(f"{prefix}{line}")
            sys.stdout.flush()
    except Exception as e:
        print(f"Error streaming {container_name}: {e}")

def signal_handler(sig, frame):
    print("\nStopping logs streams...")
    for proc in processes:
        proc.terminate()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    print("Streaming logs for control-plane, ai-engine, nginx, and redis. Press Ctrl+C to stop.\n")
    
    threads = []
    for container in containers:
        t = threading.Thread(target=stream_log, args=(container,), daemon=True)
        t.start()
        threads.append(t)
        
    # Keep main thread alive
    for t in threads:
        t.join()
