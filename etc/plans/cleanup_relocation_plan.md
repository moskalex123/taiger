# Project Cleanup and Relocation Plan

This plan outlines the relocation of non-essential files to the `etc/` directory to keep the project root clean and focused on operational files.

## Essential Files (To remain in root)

### Configuration & Environment
- [`.env`](.env)
- [`.env.prod`](.env.prod)
- [`.gitignore`](.gitignore)
- [`.node-version`](.node-version)
- [`.nvmrc`](.nvmrc)
- [`alembic.ini`](alembic.ini)
- [`package.json`](package.json)
- [`package-lock.json`](package-lock.json)
- [`requirements.txt`](requirements.txt)

### Core Logic (Python)
- [`auth.py`](auth.py)
- [`balance_utils.py`](balance_utils.py)
- [`db.py`](db.py)
- [`main.py`](main.py)
- [`models.py`](models.py)
- [`queue_manager.py`](queue_manager.py)
- [`redis_client.py`](redis_client.py)
- [`s3_avatar_manager.py`](s3_avatar_manager.py)
- [`s3_session_manager.py`](s3_session_manager.py)
- [`tg_auth.py`](tg_auth.py)
- [`tg_worker.py`](tg_worker.py)
- [`user_priority.py`](user_priority.py)
- [`worker_lock.py`](worker_lock.py)
- [`worker_manager.py`](worker_manager.py)
- [`worker_registry.py`](worker_registry.py)

### Documentation & Assets
- [`README.md`](README.md)
- [`bot_start_message.md`](bot_start_message.md)

### Essential Directories
- [`alembic/`](alembic/)
- [`api/`](api/)
- [`ctrl/`](ctrl/) (Service management)
- [`frontend/`](frontend/)
- [`git/`](git/) (Deployment scripts)
- [`locales/`](locales/)
- [`sessions/`](sessions/)
- [`static/`](static/)
- [`telegram_bot/`](telegram_bot/)
- [`telegram_worker/`](telegram_worker/)
- [`uni_text_processor/`](uni_text_processor/)

## Files to be moved to `etc/`

The following files are identified as non-essential for the immediate operation of the project or are temporary/backup files.

### SQL & Database Dumps
- [`add_newcomer_field.sql`](add_newcomer_field.sql) -> `etc/add_newcomer_field.sql`
- [`create_channel_processing_state.sql`](create_channel_processing_state.sql) -> `etc/create_channel_processing_state.sql`
- [`taigerdb_dump.sql`](taigerdb_dump.sql) -> `etc/taigerdb_dump.sql`
- [`taigerdb_new.dump`](taigerdb_new.dump) -> `etc/taigerdb_new.dump`
- [`taiger.db`](taiger.db) -> `etc/taiger.db` (SQLite database, should be in etc if not used in prod)

### Logs & Temporary Files
- [`backend.log`](backend.log) -> `etc/logs/backend.log`
- [`bot_test.log`](bot_test.log) -> `etc/logs/bot_test.log`
- [`nohup.out`](nohup.out) -> `etc/logs/nohup.out`
- [`telegram_bot.log`](telegram_bot.log) -> `etc/logs/telegram_bot.log`
- [`uvicorn.log`](uvicorn.log) -> `etc/logs/uvicorn.log`
- [`worker_7.log`](worker_7.log) -> `etc/logs/worker_7.log`
- [`project.tar.gz`](project.tar.gz) -> `etc/project.tar.gz`

### Backups & Examples
- [`.env.telegram.example`](.env.telegram.example) -> `etc/.env.telegram.example`
- [`nginx.conf.bak`](nginx.conf.bak) -> `etc/nginx.conf.bak`

### Miscellaneous
- [`README_for_AI.md`](README_for_AI.md) -> `etc/README_for_AI.md`
- [`test_connection.session`](test_connection.session) -> `etc/sessions/test_connection.session`
- [`worker_session.session`](worker_session.session) -> `etc/sessions/worker_session.session`

## Implementation Steps (GRACE)

<GRACE>
1. **Create target directories**: Ensure `etc/logs` and `etc/sessions` exist.
2. **Move SQL files**: `mv *.sql etc/`
3. **Move Log files**: `mv *.log etc/logs/` and `mv nohup.out etc/logs/`
4. **Move Archive files**: `mv project.tar.gz etc/`
5. **Move Backup/Example files**: `mv .env.telegram.example etc/` and `mv nginx.conf.bak etc/`
6. **Move Session files**: `mv *.session etc/sessions/`
7. **Move DB files**: `mv taiger.db etc/`
8. **Move AI README**: `mv README_for_AI.md etc/`
</GRACE>
