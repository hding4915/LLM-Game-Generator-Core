# Reviewer / Fixer Prompt (For Syntax & Runtime Errors)
FIXER_PROMPT = """
You are a Python Expert and QA Engineer.
I tried to run a Pygame script, but it crashed or had errors.

【CODE STRUCTURE】:
{structure}

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
Review the following game code for logical correctness:

【CODE STRUCTURE】:
{structure}

【Relevant Reference Code (from RAG)】
{context}

【Code to Review】
{code}

Please check:
1. Is it consistent with the reference code?
2. Are there any logical flaws or errors?
3. Does it use the existing functions and classes properly?

If the code passes all checks, respond only "PASS".
Otherwise, explain the issues found.
"""


# Logic Fixer Prompt
# 在 src/testing/prompts.py 中
LOGIC_FIXER_PROMPT = """
Fix the logical errors in the following game code:

【CODE STRUCTURE】:
{structure}

【Relevant Reference Examples (from RAG)】
{context}

【Current Code with Errors】
{code}

【Error Description】
{error}

Please:
1. Analyze the error based on GDD requirements
2. Reference the provided examples
3. Provide the complete fixed code

Return only the fixed code in a ```python code block.
"""

FUZZER_PROMPT = """
Here is the error: {err}, just respond the file names that cause errors.
Strictly follow the format below.
*Rules*:
1. The response should only contain the file names, one per line.
2. Do not include any additional text or explanations.

Example:
*input*
Traceback (most recent call last):
  File "/Users/jess/NCKU/Computer-Project-Design/LLM-Game-Generator-Core/output/c6a1e818-4613-4f7c-af84-cc8fd4fca156/main.py", line 36, in <module>
    main()
  File "/Users/jess/NCKU/Computer-Project-Design/LLM-Game-Generator-Core/output/c6a1e818-4613-4f7c-af84-cc8fd4fca156/main.py", line 29, in main
    game.draw(screen)
    ^^^^^^^^^
AttributeError: 'Game' object has no attribute 'draw'

*output*
main.py
"""
