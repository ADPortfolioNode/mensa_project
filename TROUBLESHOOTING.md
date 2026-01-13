# Troubleshooting Guide

## PROBLEM: Persistent "Out of Memory" Errors

The recurring `ENOMEM: not enough memory` and `OSError: [Errno 12] Cannot allocate memory` errors in both the frontend and backend containers indicate that your Docker environment does not have enough RAM allocated to run the application.

No amount of application-level configuration changes can fix this; the root cause is at the environment level.

## SOLUTION: Increase Docker's Memory Allocation

On Windows, Docker Desktop runs on the Windows Subsystem for Linux (WSL2). You need to configure the WSL2 virtual machine to have access to more of your system's RAM.

### Step 1: Edit or Create `.wslconfig` File

1.  Open Windows File Explorer.
2.  In the address bar, type `%userprofile%` and press Enter. This will take you to your user directory (e.g., `C:\Users\deois`).
3.  Look for a file named `.wslconfig`.
    *   If it **exists**, open it in a text editor like Notepad.
    *   If it **does not exist**, create a new text file and name it `.wslconfig`.

### Step 2: Add Memory Configuration

Add the following content to the `.wslconfig` file. If the file already has content, add these settings under the `[wsl2]` heading. A good starting point is 4GB of RAM.

```
[wsl2]
memory=4GB  # Allocates 4 Gigabytes of memory to WSL2
processors=2 # Allocates 2 virtual processors
```

**Note:** You can adjust the `memory` value based on your system's available RAM (e.g., `6GB` or `8GB` if you have plenty). Do not allocate all your system's RAM.

### Step 3: Restart WSL

**This is a critical step. The changes will not apply until you restart WSL.**

1.  Open a PowerShell or Command Prompt (CMD) window.
2.  Run the following command:
    ```powershell
    wsl --shutdown
    ```
3.  Wait a few moments for WSL to completely shut down. It will restart automatically the next time you use it (which will happen when you run the `start.sh` script).

### Step 4: Restart the Application

Now that Docker has more memory, return to your project terminal (`MINGW64`) and run the startup script again:

```bash
./start.sh
```

This should finally resolve the memory errors and allow the application to run successfully.