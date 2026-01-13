## Next Steps to Resolve the "Network Error"

I have made some changes to address the "Network Error" you reported. Here's a summary of what I've done and the steps you need to take to apply them.

### Summary of Changes

1.  **Standardized API URL:** I updated the frontend code to consistently use a configurable environment variable for the backend API URL. This improves maintainability but is not the primary fix for your issue.

2.  **Troubleshooting Network Error:** The "Network Error" is likely due to a networking issue on your machine, where the browser cannot connect to the backend service running in Docker. I've changed the configured URL from `http://localhost:5000` to `http://127.0.0.1:5000`. This can sometimes resolve `localhost` issues when using Docker on Windows with WSL2.

### Required Actions

For the changes to take effect, you must **rebuild and restart** your application stack. Please run the following commands in your project's root directory:

1.  **Stop the currently running services:**
    ```bash
    docker-compose down
    ```

2.  **Rebuild the services and start them in the background:**
    ```bash
    docker-compose up -d --build
    ```

The `--build` flag is important as it ensures the frontend application is rebuilt to include the updated API address.

### If the Problem Persists

After restarting, if you still encounter the "Network Error", the problem is almost certainly related to your local environment. The most common cause is a **firewall** on your Windows machine blocking connections to port `5000`.

Please check your firewall settings and create a rule to **allow incoming connections on TCP port 5000**.