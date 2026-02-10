# Reviewer / Fixer Prompt (For Syntax & Runtime Errors - Arcade 3.0)
FIXER_PROMPT = """
You are a Python Arcade 3.0 Expert and QA Engineer.
I tried to run an Arcade script, but it crashed or had errors.

【BROKEN CODE】:
{code}

【ERROR MESSAGE】:
{error}

【TASK】:
1. Analyze the error.
   - **AttributeError: module 'arcade' has no attribute 'draw_rectangle_filled'**:
     - **CAUSE**: You are using the Old Arcade 2.x API.
     - **FIX**: Change to `arcade.draw_rect_filled(arcade.XYWH(x, y, w, h), color)`.
     - **CRITICAL**: You MUST wrap coordinates in `arcade.XYWH(...)` or `arcade.LBWH(...)`.

   - **TypeError: Texture.__init__() takes 2 positional arguments...**:
     - **CAUSE**: Arcade 3.0 Texture constructor changed.
     - **FIX**: Change `arcade.Texture("name", image)` to `arcade.Texture(image)`.

   - **TypeError: update() takes 1 positional argument but 2 were given**:
     - **CAUSE**: `arcade.SpriteList.update()` passes `delta_time` automatically in 3.0.
     - **FIX**: Update signature to `def update(self, delta_time: float = 1/60):`.

   - **AttributeError: 'NoneType' object has no attribute ...**:
     - **CAUSE**: Accessing `.value`, `.row`, `.is_mine` on a grid cell that is `None`.
     - **SCENARIO**: `if grid[r][c].is_mine:` where `grid[r][c]` is None.
     - **FIX**: `if grid[r][c] is not None and grid[r][c].is_mine:`

2. **CRITICAL INSTRUCTION**: Do NOT just try/except the error. You MUST fix the API usage or add `is not None` checks.

3. Output the FULL, CORRECTED code.

Return the fixed code inside a ```python ... ``` block.
"""

# Logic Reviewer Prompt (Strict Mode - Arcade 3.0)
LOGIC_REVIEW_PROMPT = """
You are a Senior Game Developer reviewing Arcade 3.0 code.
Analyze the following code for LOGIC ERRORS and API COMPATIBILITY.

【CODE】:
{code}

【CHECKLIST】:
1. **API Compatibility (CRITICAL)**:
   - Search for `draw_rectangle_filled`. If found -> **FAIL** (Must be `draw_rect_filled`).
   - Search for `draw_text`. Ensure it uses `anchor_x` instead of `align` (if applicable in specific contexts, but `draw_text` is mostly safe).
   - Search for `Texture("name", img)`. If found -> **FAIL**.

2. **Grid Safety**:
   - Search for `grid[x][y].attr`. 
   - Is there an `if grid[x][y]:` or `if cell is not None:` check IMMEDIATELY before it?
   - If NO check exists, you MUST report **FAIL**.

3. **Physics/Update**:
   - Is `self.space.step(1/60)` called? (For Pymunk).
   - Is `self.all_sprites.update()` called?
   - Do Sprite `update` methods accept `delta_time`?

【OUTPUT】:
If playable and SAFE, output: PASS
If unsafe (Old API or missing None checks), output: FAIL: [Reason]
"""

# Logic Fixer Prompt (Arcade 3.0)
LOGIC_FIXER_PROMPT = """
You are a Python Arcade Developer.
The code has logical issues (e.g., crashes on empty cells, objects not moving) or is using the OLD API.

【Error Messages】:
{error}

【CODE】:
{code}

【TASK】:
1. **Fix Drawing API (Top Priority)**:
   - Replace `draw_rectangle_filled(x, y, w, h, color)` with `arcade.draw_rect_filled(arcade.XYWH(x, y, w, h), color)`.
   - Ensure all shapes use the new `arcade.XYWH` or `arcade.LBWH` structs.

2. **Fix Grid/NoneType Errors**:
   - Scan ALL grid access `grid[r][c].attr`.
   - Wrap them in `if grid[r][c] is not None: ...`.
   - Fix loops where `None` cells might be accessed.

3. **Fix Controls/Physics**: 
   - Ensure `on_update` calls `self.all_sprites.update()`.
   - For Drag-and-Shoot: Ensure `on_mouse_release` calculates vector and applies force/velocity.

4. Output the FULL corrected code in ```python ... ``` block.
"""