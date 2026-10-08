error: failed to solve: failed to calculate checksum ... "/save_auth_state.py": not found
```[cite: 3]

This means Docker found `watcher.py`, but it cannot locate `save_auth_state.py` in the root folder[cite: 3].

---

### Step-by-Step Fixes

1. **Verify the Exact File Name & Case**
   Check that `save_auth_state.py` exists in your repository root directory and matches the exact spelling and lowercase characters[cite: 3].
   * **Verification:** Run `ls save_auth_state.py` (Linux/macOS) or `dir save_auth_state.py` (Windows PowerShell) in your local project folder to confirm it is listed.

2. **Check Git Tracking**
   If you deploy via Git push (GitHub/GitLab/Render/Koyeb), the file might exist locally but hasn't been committed to Git[cite: 3].
   * Run:
     ```bash
     git status
     ```
   * If `save_auth_state.py` appears under **Untracked files**, stage and commit it:
     ```bash
     git add save_auth_state.py
     git commit -m "Add save_auth_state.py"
     git push
     ```
   * **Verification:** Run `git ls-files save_auth_state.py`. If it outputs `save_auth_state.py`, the file is properly tracked by Git.

3. **Check `.gitignore` and `.dockerignore`**
   Ensure neither `.gitignore` nor `.dockerignore` contains rules excluding Python files (e.g., `*.py` or `save_auth_state.py`).
   * **Verification:** Run `git check-ignore -v save_auth_state.py` in your terminal. If it returns nothing, Git is not ignoring the file.

4. **Separate the COPY Instructions (Alternative)**
   If one of the files is optional or dynamically generated, split the line in your `Dockerfile`:
   ```dockerfile
   COPY watcher.py ./
   COPY save_auth_state.py ./
