This is a final attempt to resolve the persistent `chroma` container healthcheck issue.

The problem is that the `chroma` container starts, but the `healthcheck` command fails, which prevents the rest of the application from starting.

I have made one last change to `docker-compose.yml`:
-   The `healthcheck` command for the `chroma` service has been changed from `curl` to `wget`. This is to rule out any issues with `curl` inside that specific container.

**Please run the startup command one last time:**

```
docker-compose up -d --build
```

**If the problem still persists:**

This indicates a high probability of an issue within the `chromadb/chroma:latest` Docker image itself, or a fundamental incompatibility with your Docker environment.

The next logical step would be to stop using the `latest` tag and instead pin the service to a specific, known-good version. I would recommend trying `0.4.24`, which is a recent, stable version.

To do this, you would change this line in `docker-compose.yml`:
```yaml
image: chromadb/chroma:latest
```
to this:
```yaml
image: chromadb/chroma:0.4.24
```

This is the last troubleshooting step I can provide.