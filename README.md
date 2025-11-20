# Pi Backup Manager

A lightweight FastAPI-based web UI for configuring and running backups on a Raspberry Pi. It backs up local paths to a destination such as a USB drive or network mount, using `rsync` when available and falling back to Python file copy.

## Features
- Web UI (FastAPI + Jinja2) at `http://<pi-ip>:8080`.
- Browse allowed root paths and select files/folders to back up.
- Save selections to `backup_config.json` in the project directory.
- Run backups manually and view logs from the UI.
- Timestamped backup folders with retention (keep last N or delete older than N days).
- Uses `rsync` if installed, else falls back to `shutil` copy.

## Project layout
```
pi-backup-manager/
  app/
    main.py            # FastAPI entrypoint
    api.py             # JSON API routes
    views.py           # HTML routes
    templates/         # Jinja2 templates
    static/            # CSS
    backup/
      engine.py        # Backup runner + logging
      retention.py     # Retention pruning
      config.py        # Config load/save
      filesystem.py    # Safe filesystem browsing helpers
  backup_config.json   # Created on first run
  requirements.txt
  run.sh
  systemd-service-example.txt
```

## Installation (Raspberry Pi OS)
1. Ensure Python 3.11+ is installed (`python3 --version`).
2. Install system dependencies:
   ```bash
   sudo apt update
   sudo apt install python3-venv rsync
   ```
3. Clone or copy this folder onto the Pi (e.g., `/home/pi/pi-backup-manager`).
4. Create a virtual environment and install Python deps:
   ```bash
   cd ~/pi-backup-manager
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

## Running the server
- Development / manual run:
  ```bash
  source .venv/bin/activate
  ./run.sh
  # Open http://<pi-ip>:8080
  ```
- Configure environment variables as needed:
  - `PI_BACKUP_HOST` (default `0.0.0.0`)
  - `PI_BACKUP_PORT` (default `8080`)

## Config file
`backup_config.json` is created automatically with defaults on first run. You can also edit it manually while the server is stopped.

Example:
```json
{
  "destination": "/mnt/backups",
  "selected_paths": ["/home/pi/shared"],
  "allowed_roots": ["/home/pi", "/mnt", "/media"],
  "include_patterns": [],
  "exclude_patterns": [],
  "retention": {
    "keep_last": 3,
    "max_age_days": null
  }
}
```

## Running a backup manually (CLI)
You can invoke the backup engine directly without the web UI:
```bash
source .venv/bin/activate
python -m app.backup.engine
```

## Systemd service example
See `systemd-service-example.txt` for a sample unit file to run the web server at boot.

## Logs
Logs are written to `logs/backup.log` with rotation. The UI exposes the last few hundred lines.

## Tests / validation
This project is intentionally small; manual validation steps:
1. Start the server (`./run.sh`).
2. Navigate to `/browse`, select one or two directories, and hit **Save Selection**.
3. Click **Run Backup** on the home page.
4. Verify a new timestamped folder appears under the configured destination and the **Logs** page shows the run.
