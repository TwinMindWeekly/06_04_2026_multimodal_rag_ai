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
