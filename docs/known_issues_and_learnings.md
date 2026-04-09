# Known Issues & Learnings Log

Welcome to the AI Agent Continuous Learning Log. Every time a bug is caught and fixed, document it here to prevent regressions in the future.

## 1. Vite HMR Crash due to missing React Imports
- **Date**: 09-04-2026
- **Issue**: Modifying `main.jsx` to configure `i18n` caused `StrictMode` to throw a `ReferenceError`.
- **Root Cause**: `import { StrictMode } from 'react'` was accidentally deleted during the `replace_file_content` action.
- **Solution**: Re-added the import. 
- **Precaution for Future**: Always preserve existing React standard imports when replacing blocks in the root render file.

## 2. Vite Build Issue with Relative Pathing
- **Date**: 09-04-2026
- **Issue**: Vite threw a resolution error when `i18n.js` attempted to load `./locales/vi.json`.
- **Root Cause**: The path was written as `../locales/vi.json` instead of `./locales/...` while both were in `src/`.
- **Solution**: Changed to relative sibling path.

## 3. Axios 404 on API Routes
- **Date**: 09-04-2026
- **Issue**: Axios returned 404 when fetching `/projects/`.
- **Root Cause**: FastAPI `APIRouter` used `prefix="/api/projects"`, but Axios base URL was set to `http://localhost:8000` (missing `/api`).
- **Solution**: Patched `baseURL` to append `/api`.
- **Learning**: Always cross-check the FastAPI APIRouter prefix with the frontend Axios `baseURL`.

## 4. Document Upload Fails Without Context
- **Date**: 09-04-2026
- **Issue**: Calling `/api/documents/upload` directly resulted in a Form Validation Error.
- **Root Cause**: FastAPI endpoint explicitly required `folder_id: int = Form(...)` with no fallback.
- **Solution**: Allowed null uploads by changing to `folder_id: int = Form(None)`.

## 5. FastAPI BackgroundTask Database Session Leak
- **Date**: 09-04-2026
- **Issue**: Passing `db: Session` from a router endpoint (which uses `Depends(get_db)`) to a BackgroundTask causes a `DetachedInstanceError` or `SessionClosedError` because FastAPI generator tears down the session before the background task finishes.
- **Root Cause**: FastAPI `yield db` automatically shuts down the DB session once the HTTP Response is returned. Background Tasks run after the response.
- **Solution**: Do NOT pass the HTTP session to background tasks. Instead, pass the ID (e.g., `document_id`) and explicitly create a local session (`db = SessionLocal()`) and close it inside the background function `finally: db.close()`.

## 6. OOM (Out-of-Memory) Vulnerability on Document Upload
- **Date**: 09-04-2026
- **Issue**: High memory consumption when users upload large PDFs.
- **Root Cause**: `await file.read()` evaluates the entire byte payload into a single object in RAM before writing it out.
- **Solution**: Refactored logic to use Python's buffered stream `shutil.copyfileobj(file.file, buffer)`.

## 7. DB Lock-in Deletion Failure
- **Date**: 09-04-2026
- **Issue**: Cannot delete a Document entry from the SQLite DB if the associated physical file (`os.remove()`) fails to delete.
- **Root Cause**: Deleting a physical file can fail (PermissionError or FileNotFoundError), throwing a 500 sequence without reaching `db.delete()`. 
- **Solution**: Sandwiched `os.remove()` inside a standard `try-except` block to guarantee graceful rollback and assure database integrity synchronization.
