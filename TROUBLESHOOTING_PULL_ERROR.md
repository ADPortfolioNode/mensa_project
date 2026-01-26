I have corrected the `docker-compose.yml` file.

The error `unrecognized subcommand 'chroma'` was caused by a small error in the `command` for the `chroma` service. The command was `chroma run ...`, but the Docker image entrypoint is already the `chroma` executable.

The command has been corrected to `run --host 0.0.0.0 --port 8000 --path /chroma`.

Please try running `docker-compose up -d` again.