# Troubleshooting Steps

I have identified a potential issue with the application related to a version mismatch of the `chromadb` package.

## Changes Made

I have downgraded the version of `chromadb` in `backend/requirements.txt` from `1.3.5` to `0.3.30`.

## Next Steps

To apply the changes and restart the application, please run the following command in your terminal:

```bash
docker-compose up --build -d
```
