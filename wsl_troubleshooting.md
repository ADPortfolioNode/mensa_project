# Troubleshooting WSL 2 Networking Issues

When you run servers inside Docker on WSL 2, they bind to `localhost` *within the WSL environment*. Sometimes, these ports are not automatically forwarded to `localhost` on your Windows host machine, which prevents you from accessing them in your browser.

Here is the recommended solution to ensure that ports are correctly forwarded.

## Step 1: Edit your `.wslconfig` file

You need to ensure that WSL is configured to forward localhost ports.

1.  Open Windows PowerShell or Command Prompt.
2.  Open your WSL configuration file in notepad by running:
    ```shell
    notepad C:\Users\deois\.wslconfig
    ```
3.  Add the following content to the file. If the file already has a `[wsl2]` section, add the `localhostForwarding` key to it.

    ```ini
    [wsl2]
    localhostForwarding=true
    ```

4.  Save the file and close the editor.

## Step 2: Restart WSL

For the changes in `.wslconfig` to take effect, you must shut down and restart the WSL instance.

1.  Open Windows PowerShell or Command Prompt.
2.  Run the following command:
    ```shell
    wsl --shutdown
    ```
    This command will stop all running WSL distributions.

## Step 3: Restart Your Application

1.  Navigate back to your project directory (`e:\2024 RESET\mensa_project`) in your WSL terminal.
2.  Start your Docker containers again:
    ```shell
    docker-compose up -d --build
    ```

## Step 4: Access the Application

After the containers have started, open your web browser on Windows and navigate to:

**http://localhost:3000**

You should now be able to see your frontend application.
