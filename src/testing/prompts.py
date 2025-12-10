# Reviewer / Fixer Prompt
FIXER_PROMPT: str = """
You are a Python Expert and QA Engineer.
I tried to run a Pygame script, but it crashed or had logic errors.

【BROKEN CODE】:
{code}

【ERROR MESSAGE / LOGIC ISSUE】:
{error}

【TASK】:
1. Analyze the error message and the code.
2. Fix the error (e.g., missing imports, undefined variables, logic errors, unresponsive controls).
3. Output the FULL, CORRECTED code.
4. Ensure the code still follows the structure:
    - import pygame
    - pygame.init()
    - Game Loop
    - if __name__ == "__main__":

Return the fixed code inside a ```python ... ``` block.
"""

# 新增：邏輯審查 Prompt
LOGIC_REVIEW_PROMPT = """
You are a Senior Game Developer reviewing Pygame code.
Analyze the following code for LOGIC ERRORS, specifically regarding CONTROLS and MOVEMENT.

【CODE】:
{code}

【CHECKLIST】:
1. Is `pygame.key.get_pressed()` called inside the main loop?
2. Are movement keys (WASD or Arrows) actually modifying the player's `rect.x` / `rect.y` or position variables?
3. Is the player's speed/velocity non-zero? (Look for `speed = 0` bugs)
4. Is `pygame.event.get()` called correctly to prevent freezing?
5. Is the screen updated with `pygame.display.flip()` or `update()`?

【OUTPUT FORMAT】:
If the code is good and playable:
PASS

If there are logic issues (e.g., player cannot move, missing update), output:
FAIL: [Brief explanation of the error]
"""