I have updated the `docker-compose.yml` file to fix the communication issue between the frontend and backend containers.

The `REACT_APP_API_BASE` environment variable for the frontend service has been changed to `http://backend:5000`. This allows the frontend to find the backend service on Docker's internal network.

**Next Steps:**

1.  **Rebuild and start the services:**
    Open a terminal in the project root and run this command:
    ```
    docker-compose up -d --build
    ```

2.  **Verify the application:**
    Once the containers are running, open your web browser and navigate to:
    [http://localhost:3000](http://localhost:3000)

The application should now be working correctly.