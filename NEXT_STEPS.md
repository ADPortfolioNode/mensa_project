I have updated the `docker-compose.yml` to use a more recent version of ChromaDB.

Please run the following command in your terminal to apply the changes and restart the services:

```bash
docker-compose up -d --build --force-recreate
```

The `--build` flag is important to ensure that the new image is pulled.

If the `mensa_chroma` container still fails to start, it's likely that the `e:\2024 RESET\mensa_project\data\chroma` directory contains corrupted data from the old version. In that case, please follow these steps:

1.  Stop the services:
    ```bash;
    docker-compose down
    ```
2.  Delete the chroma data directory:
    ```bash
    rm -rf "e:\2024 RESET\mensa_project\data\chroma"
    ```
3.  Restart the services:
    ```bash
    docker-compose up -d
    ```

This will ensure that the `chroma` service starts with a completely fresh and empty data directory.
