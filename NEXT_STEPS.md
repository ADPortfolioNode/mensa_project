I have updated the game lists to include all the additional lottery games that can be ingested from data.ny.gov.

**Summary of Changes**

*   **Added New Games:** I have added the following games to both `DATASET_ENDPOINTS` and `GAME_CONFIGS` in `backend/config.py`:
    *   Powerball
    *   NY Lotto
    *   Mega Millions
    *   Pick 10
    *   Cash 4 Life
    *   Quick Draw

**Next Steps**

To apply these changes, you need to rebuild and restart the backend service. I am unable to do this for you.

Please run one of the following commands in your terminal:

```bash
# Option 1: Rebuild and restart only the backend service
docker-compose build backend && docker-compose up -d backend
```

or

```bash
# Option 2: Run the start script to rebuild and restart all services
./start.sh
```

After running one of these commands, the application should reflect the updated list of ingestible games.
