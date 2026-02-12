#!/usr/bin/env python3
"""
Monitor Docker Compose startup and capture errors
"""
import subprocess
import sys
import os

os.chdir(r'e:\2024 RESET\mensa_project')

# Ensure GEMINI_API_KEY is set
if 'GEMINI_API_KEY' not in os.environ:
    # Try to read from .env
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('GEMINI_API_KEY='):
                    key = line.split('=', 1)[1].strip()
                    if key:
                        os.environ['GEMINI_API_KEY'] = key
                        print(f"Loaded GEMINI_API_KEY from .env")
                        break
    except:
        pass

print("Starting Docker Compose...")
print("=" * 80)

try:
    proc = subprocess.Popen(
        ['docker', 'compose', 'up', '--build'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    output_lines = []
    error_keywords = ['error', 'fail', 'exception', 'timeout', 'refused', 'cannot', 'unhealthy']
    
    for line in proc.stdout:
        print(line, end='')
        output_lines.append(line)
        # Alert on errors
        if any(err_kw in line.lower() for err_kw in error_keywords):
            print(f">>> ERROR DETECTED: {line.strip()}", file=sys.stderr)
    
    proc.wait()
    
    # Save output to file
    with open('startup_output.txt', 'w') as f:
        f.writelines(output_lines)
    
    print("=" * 80)
    print(f"Process exited with code: {proc.returncode}")
    print(f"Output saved to: startup_output.txt")
    
except KeyboardInterrupt:
    print("\nInterrupted by user")
    proc.terminate()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
