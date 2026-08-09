# Local Development

The current development environment runs entirely in OrbStack. MariaDB, Redis, Bench, Frappe,
workers, the scheduler, the asset watcher, and the realtime service are not installed on macOS.

Run these commands from the outer Frappe workspace root.

## Start

```bash
./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml up -d
```

Open <http://college.localhost:8000> and sign in with the local-only credentials:

- User: `Administrator`
- Password: `admin`

## Status and logs

```bash
./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml ps
./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml logs -f server
```

## Bench shell

```bash
./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml exec frappe bash
cd /workspace/development/frappe-bench
```

## Test the custom app

```bash
./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml exec -T \
  -w /workspace/development/frappe-bench frappe \
  bench --site college.localhost run-tests --app college_management
```

## Stop

```bash
./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml down
```

Do not add `--volumes` to the stop command unless the development database is intentionally being
discarded.

## Pinned baseline

- Frappe: `v16.30.0` (`9523516cac25992bc2cd810e1015df8994c257f5`)
- Python: `3.14.2`
- Node.js: `24.13.0`
- Bench: `5.31.0`
- MariaDB image: `11.8`, pinned by digest in Compose
- Redis image: `7-alpine`, pinned by digest in Compose
- Bench image: pinned by digest in Compose
