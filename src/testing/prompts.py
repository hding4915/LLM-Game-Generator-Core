# Reviewer / Fixer Prompt (For Syntax & Runtime Errors)
FIXER_PROMPT = """
You are a Python Expert and QA Engineer.
I tried to run a Pygame script, but it crashed or had errors.

【BROKEN CODE】:
{code}

【ERROR MESSAGE】:
{error}

【TASK】:
1. Analyze the error.
   - **AttributeError: 'NoneType' object has no attribute ...**:
     - **CAUSE**: You are accessing `.value`, `.row`, `.rect` on a grid cell that is `None`.
     - **SCENARIO 1 (Comparison)**: `if grid[r][c].value == grid[r+1][c].value`
       - **FIX**: `if grid[r][c] is not None and grid[r+1][c] is not None and grid[r][c].value == grid[r+1][c].value:`
     - **SCENARIO 2 (Assignment)**: `grid[r][c].row = r`
       - **FIX**: `if grid[r][c] is not None: grid[r][c].row = r`
     - **SCENARIO 3 (Method Call)**: `tile.update()`
       - **FIX**: `if tile is not None: tile.update()`

   - **TypeError ... missing argument**:
     - **FIX**: Define `def update(self, *args):` in Sprite classes.

2. **CRITICAL INSTRUCTION**: Do NOT just try/except the error. You MUST add the `if ... is not None` check logic.

3. Output the FULL, CORRECTED code.

Return the fixed code inside a ```python ... ``` block.
"""

# Logic Reviewer Prompt (Strict Mode)
LOGIC_REVIEW_PROMPT = """
You are a Senior Game Developer reviewing Pygame code.
Analyze the following code for LOGIC ERRORS. Do NOT hallucinate checks that aren't there.

【CODE】:
{code}

【CHECKLIST】:
1. **Grid Safety (CRITICAL)**:
   - Search for `grid[x][y].value` or `cell.attr`. 
   - Is there an `if grid[x][y]:` or `if cell is not None:` check IMMEDIATELY before it?
   - If NO check exists, you MUST report **FAIL**.
   - Example: `grid[r][c].value` without check -> **FAIL**.

2. **Physics/Update**:
   - Is `self.rect.center` updated by `self.pos`?
   - Is `pygame.display.flip()` called?

3. **Controls**:
   - Are keys/mouse inputs handled?

【OUTPUT】:
If playable and SAFE, output: PASS
If unsafe (missing None checks), output: FAIL: [Line number/Function] accesses NoneType without check.
"""

# Logic Fixer Prompt
LOGIC_FIXER_PROMPT = """
You are a Python Game Developer.
The code has logical issues (e.g., crashes on empty cells, objects not moving).

【CODE】:
{code}

【TASK】:
1. **Fix Grid/NoneType Errors (Top Priority)**:
   - Scan ALL grid access `grid[r][c].attr`.
   - Wrap them in `if grid[r][c]: ...`.
   - Fix loops where `None` cells might be accessed.
2. **Fix Physics/Controls**: 
   - Ensure `update()` updates position.
   - Ensure Mouse Drag calculates vector correctly.
3. Output the FULL corrected code in ```python ... ``` block.
"""