The project is now configured for the most stable setup.

Your `docker-compose.yml` file has already been updated to use a specific, stable version of the Chroma database (`chromadb/chroma:0.4.24`) instead of the volatile `:latest` tag. This is the industry-standard and most reliable way to ensure your development environment is predictable and stable.

To ensure all old, potentially problematic containers are removed and you start with a completely clean slate, please follow these steps exactly.

### Final Deployment Checklist

**1. Stop and Remove All Containers**
This command will stop and remove all services defined in your `docker-compose.yml` file.
```bash
docker-compose down --remove-orphans
```

**2. Clean Your Docker System**
This is a powerful command that will remove all stopped containers, all networks not used by at least one container, all dangling images, and all build cache. It will also remove all unused volumes. This ensures there is no lingering data from previous failed attempts.
```bash
docker system prune -a -f --volumes
```

**3. Build and Start the Services**
This is the final command. It will pull the specific, stable version of ChromaDB and build your local services.
```bash
docker-compose up -d --build
```

After running these commands, the application will be running in a stable and correct configuration.

- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:5000](http://localhost:5000)