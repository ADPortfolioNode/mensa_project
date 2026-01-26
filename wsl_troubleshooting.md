# WSL Troubleshooting Guide

If you are running Docker on Windows with the WSL 2 backend, you might encounter performance issues or errors related to resource limits (memory and disk space). This is because Docker Desktop runs within a virtual machine managed by WSL 2. Over time, this VM's virtual disk can grow very large and it might not release memory back to the host system efficiently.

Here are some steps to reclaim disk space and reset Docker's resource usage on WSL.

## Step 1: Check WSL Status

First, open PowerShell or Command Prompt and check the status of your WSL distributions.

```powershell
wsl -l -v
```

You should see output like this. The `docker-desktop` and `docker-desktop-data` distributions are the ones we are interested in.

```
  NAME                   STATE           VERSION
* Ubuntu-20.04           Running         2
  docker-desktop-data    Running         2
  docker-desktop         Running         2
```

## Step 2: Shut Down Docker and WSL

To safely perform maintenance, you need to shut down Docker Desktop and all running WSL instances.

1.  **Quit Docker Desktop:** Right-click the Docker icon in your system tray and select "Quit Docker Desktop".
2.  **Shut down WSL:** In your terminal, run the following command. This will terminate all running distributions.

    ```powershell
    wsl --shutdown
    ```

    Wait a few moments for it to complete. You can run `wsl -l -v` again to confirm that all distributions are in the `Stopped` state.

## Step 3: Reclaim Disk Space (Compact Virtual Disk)

WSL 2 stores each distribution in its own virtual hard disk file (`.vhdx`). When you delete files inside WSL, the `.vhdx` file does not automatically shrink. You can manually compact it.

1.  **Find the `diskpart` command-line tool.** It's a built-in Windows utility.
2.  **Run the script:** You will need to find the path to your `docker-desktop-data` VHDX file. It's usually located in a path like:
    `%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx`
3.  **Open a Command Prompt as Administrator** and run the following commands, replacing the path with the correct one for your system if it's different.

    ```batch
    # First, start the diskpart utility
    diskpart

    # Inside diskpart, select the virtual disk
    select vdisk file="%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx"

    # Compact the disk
    compact vdisk

    # Exit diskpart
    exit
    ```

This process can take a few minutes and will shrink the `.vhdx` file, reclaiming potentially gigabytes of space on your host machine.

## Step 4: Restart Docker

Once the process is complete, you can restart Docker Desktop. It will automatically restart the required WSL distributions.

Your Docker environment should now be in a cleaner state, with more available disk space and reset memory usage.

## Optional: Limiting WSL Memory Usage

By default, WSL 2 will consume up to 50% of your total RAM. If you find it's using too much memory, you can limit it by creating a `.wslconfig` file in your user profile directory (`C:\Users\<YourUsername>`).

1.  Create a file named `.wslconfig` in `C:\Users\<YourUsername>\`.
2.  Add the following content to limit memory, for example, to 4GB:

    ```
    [wsl2]
    memory=4GB
    processors=2
    ```

3.  Save the file and run `wsl --shutdown` for the changes to take effect. The next time WSL starts, it will respect these limits. Be aware that setting this too low can cause services like ChromaDB to fail, so you may need to experiment to find a good balance for your system.