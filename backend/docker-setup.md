# Docker PostgreSQL Setup for SlotFit

## Step 1: Start Docker Desktop

1. Open Docker Desktop application
2. Wait for it to fully start (whale icon in system tray should be steady)
3. Verify it's running by checking the Docker Desktop window

## Step 2: Create PostgreSQL Container

Run this command to create and start a PostgreSQL container:

```bash
docker run --name slotfit-db -e POSTGRES_PASSWORD=slotfit -e POSTGRES_DB=slotfit -p 5432:5432 -d postgres:15
```

**What this does:**
- `--name slotfit-db` - Names the container "slotfit-db"
- `-e POSTGRES_PASSWORD=slotfit` - Sets password to "slotfit"
- `-e POSTGRES_DB=slotfit` - Creates database "slotfit"
- `-p 5432:5432` - Maps port 5432 (host) to 5432 (container)
- `-d` - Runs in detached mode (background)
- `postgres:15` - Uses PostgreSQL version 15

## Step 3: Verify Container is Running

```bash
docker ps
```

You should see `slotfit-db` in the list.

## Step 4: Test Connection (Optional)

```bash
docker exec -it slotfit-db psql -U postgres -d slotfit -c "SELECT version();"
```

## Step 5: Configure Backend

Create `backend/.env` file with:

```env
DATABASE_URL=postgresql+asyncpg://postgres:slotfit@localhost:5432/slotfit
AI_PROVIDER=claude
ANTHROPIC_API_KEY=
API_V1_PREFIX=/api/v1
DEBUG=True
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## Useful Docker Commands

```bash
# Stop container
docker stop slotfit-db

# Start container (if stopped)
docker start slotfit-db

# Remove container (if you need to recreate)
docker rm -f slotfit-db

# View logs
docker logs slotfit-db

# Access PostgreSQL shell
docker exec -it slotfit-db psql -U postgres -d slotfit
```
