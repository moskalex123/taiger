# Project Cleanup and Relocation Plan

This plan outlines the reorganization of the project directory to keep only essential and service files in the root, moving everything else to `taiger/etc`.

## 1. Essential Files (Stay in Root)
These files are required for the application to run, build, or are standard configuration files.

### Core Application
- [`main.py`](main.py) - Entry point for the FastAPI application.
- [`auth.py`](auth.py) - Authentication logic.
- [`db.py`](db.py) - Database connection and session management.
- [`models.py`](models.py) - SQLAlchemy models.
- [`redis_client.py`](redis_client.py) - Redis connection management.
- [`queue_manager.py`](queue_manager.py) - Task queue management.
- [`worker_manager.py`](worker_manager.py) - Worker process management.
- [`worker_registry.py`](worker_registry.py) - In-memory worker tracking.
- [`tg_auth.py`](tg_auth.py) - Telegram authentication logic.
- [`tg_worker.py`](tg_worker.py) - Telegram worker implementation.
- [`balance_utils.py`](balance_utils.py) - Balance calculation utilities.
- [`s3_avatar_manager.py`](s3_avatar_manager.py) - S3 storage for avatars.
- [`s3_session_manager.py`](s3_session_manager.py) - S3 storage for sessions.
- [`user_priority.py`](user_priority.py) - User priority logic.
- [`worker_lock.py`](worker_lock.py) - Locking mechanism for workers.

### Configuration & Environment
- [`.env`](.env) - Environment variables.
- [`.env.prod`](.env.prod) - Production environment variables.
- [`.gitignore`](.gitignore) - Git ignore rules.
- [`.node-version`](.node-version) - Node.js version config.
- [`.nvmrc`](.nvmrc) - NVM configuration.
- [`alembic.ini`](alembic.ini) - Database migration config.
- [`package.json`](package.json) - Node.js dependencies.
- [`package-lock.json`](package-lock.json) - Node.js lockfile.
- [`requirements.txt`](requirements.txt) - Python dependencies.

### Essential Directories
- [`alembic/`](alembic/) - Database migrations.
- [`api/`](api/) - FastAPI route handlers.
- [`frontend/`](frontend/) - Frontend source code and build.
- [`locales/`](locales/) - Localization files.
- [`static/`](static/) - Static assets.
- [`telegram_bot/`](telegram_bot/) - Telegram bot implementation.
- [`telegram_worker/`](telegram_worker/) - Worker-specific logic.
- [`uni_text_processor/`](uni_text_processor/) - Text processing modules.
- [`sessions/`](sessions/) - Telegram session storage (if local).

## 2. Service Files (Stay in Root/Folders)
As per instructions, files in `git/` and `ctrl/` folders stay.

- [`git/`](git/) - Deployment and GitHub integration scripts.
- [`ctrl/`](ctrl/) - Service management scripts.

## 3. Files to Move to `taiger/etc`
These are non-essential files, logs, backups, temporary scripts, and documentation that are not required for the runtime.

### Logs & Temporary Files
- `backend.log`
- `bot_test.log`
- `telegram_bot.log`
- `uvicorn.log`
- `worker_7.log`
- `nohup.out` (if present)
- `taiger.db` (SQLite DB, should be in a data folder or etc if not used in prod)
- `taigerdb_dump.sql`
- `taigerdb_new.dump`
- `test_connection.session`
- `worker_session.session`

### Documentation & Reports
- [`README.md`](README.md) (Move to etc, or keep a minimal one in root)
- [`README_for_AI.md`](README_for_AI.md)
- [`user_guide.md`](user_guide.md)
- [`user_instruction.md`](user_instruction.md)
- [`user_manual.md`](user_manual.md)
- [`users_guide_full.md`](users_guide_full.md)
- [`language_switching_implementation_report.md`](language_switching_implementation_report.md)
- [`localization_plan.md`](localization_plan.md)
- [`project_analysis_report.md`](project_analysis_report.md)
- [`docs/`](docs/) (Entire directory)
- [`plans/`](plans/) (Entire directory)

### Scripts (Non-Service)
- `auto_setup_aux_vps_access.sh`
- `check-ui-state.js`
- `deploy-to-production.sh`
- `enable-new-ui.bat`
- `enable-new-ui.sh`
- `fix-vps-dns.sh`
- `install_taiger.sh`
- `manual_register_worker.sh`
- `monitor_logs.py`
- `monitor_worker_status.py`
- `newcomer_cleanup_task.py` (If not imported in main)
- `pull-from-vps.ps1`
- `re_front.sh`
- `setup_aux_vps_access.sh`
- `setup_passwordless_aux_vps.sh`
- `setup_ssh_access.sh`
- `simple-verify.bat`
- `start_dev.sh`
- `start.sh`
- `switch-to-develop.sh`
- `switch-to-main.sh`
- `sync-to-vps.ps1`
- `test_balance_functionality.py`
- `test_balance_simple.py`
- `test_keyboard_localization.py`
- `test_language_switching.py`
- `test_status_race_condition.py`
- `find_channel.py`
- `debug_user_16.py`

### Other
- `project.tar.gz`
- `public_key_aux.txt`
- `ssh_config`
- `taiger-api.service` (Should be in `/etc/systemd/system/`, copy in root is backup)
- `taiger-frontend.service`
- `ubprocess` (likely a typo or temp file)
- `ystemctl status taiger-api` (typo file)
- `micro-client-for-self-test/`
- `add_newcomer_field.sql`
- `create_channel_processing_state.sql`
- `nginx.conf` / `nginx_current.conf` / `nginx_fixed.conf` / `nginx.conf.bak`

## Relocation Commands (GRACE)

```bash
# Create destination directory
mkdir -p taiger/etc

# Move files (example)
# mv backend.log taiger/etc/
# ...
```

**Note:** I will wait for your approval before proceeding with the actual move.
