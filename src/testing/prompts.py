# Reviewer / Fixer Prompt (For Syntax & Runtime Errors)
FIXER_PROMPT = """
You are a Python Expert and QA Engineer.
I tried to run a Pygame script, but it crashed or had errors.

【BROKEN CODE】:
{code}

【ERROR MESSAGE】:
{error}

【TASK】:
1. Analyze why the error happened.
   - If `NameError` (e.g., 'pockets' is not defined), checking variable scope.
   - If `TypeError: ... missing 1 required positional argument` in `update()`:
     - **FIX**: Make `update()` accept `*args` (e.g., `def update(self, *args):`).
   - If `AttributeError: 'NoneType' object has no attribute ...`:
     - **CRITICAL**: This happens when you try to access an attribute (like `.value`, `.rect`, `.pos`) of a variable that is `None`.
     - **Common Cause**: Empty grid cells in puzzle games (2048, Tetris) or dead sprites.
     - **FIX**: You MUST add a check `if object is not None:` BEFORE accessing the attribute.
     - Example: Change `if grid[x][y].value == 2:` to `if grid[x][y] is not None and grid[x][y].value == 2:`

2. Fix the code.
3. Output the FULL, CORRECTED code.
4. Ensure the code still follows the structure.

Return the fixed code inside a ```python ... ``` block.
"""

# Logic Reviewer Prompt
LOGIC_REVIEW_PROMPT = """
You are a Senior Game Developer reviewing Pygame code.
Analyze the following code for LOGIC ERRORS.

【GDD requirements】:
{gdd}

【CODE】:
{code}

【CHECKLIST】:
1. Is `pygame.key.get_pressed()` called inside the main loop?
2. Are movement keys actually updating position?
3. Is `pygame.display.flip()` or `update()` called?
4. **Physics Check**:
   - Is `self.rect.center` or `self.pos` updated by `self.velocity` in the `update()` loop?
   - Is `friction` too high? (Should be around 0.98 or 0.99, NOT 0.5 or lower).
5. **Mouse Dragging**:
   - Does `MOUSEBUTTONUP` calculate a vector and apply it to `self.velocity`?

【OUTPUT】:
If playable, output strictly: PASS
If broken, output: FAIL: [Reason]
"""

# Logic Fixer Prompt (強制修復物理)
LOGIC_FIXER_PROMPT = """
You are a Python Game Developer.
The code has logical issues (e.g., objects not moving, controls unresponsive).


【GDD requirements】:
{gdd}

【CODE】:
{code}

【TASK】:
1. **Fix Physics Update**: 
   - Ensure `self.pos += self.velocity` is present in `update()`.
   - Ensure `self.rect.center` is updated from `self.pos`.
2. **Fix Mouse Control**:
   - For Drag-to-Shoot games: Ensure `MOUSEBUTTONUP` calculates `(start - end)` and sets `self.velocity`.
   - Ensure Force Multiplier is strong enough (e.g., `vector * 0.1` might be too weak, try `vector * 0.5`).
3. **Fix Friction**:
   - Ensure friction is NOT too strong (Use `0.99` instead of `0.8`).
4. Output the FULL corrected code in ```python ... ``` block.
"""