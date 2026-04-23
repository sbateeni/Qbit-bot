Real-world code examples demonstrating the four Karpathy Principles. Each example shows what LLMs commonly do wrong and how to fix it.

---

### Example 1: Hidden Assumptions
**User Request:** "Add a feature to export user data"

**❌ What LLMs Do (Wrong Assumptions)**
- Assumed it should export ALL users.
- Assumed file location without asking.
- Assumed which fields to include.

**✅ What Should Happen (Surface Assumptions)**
State assumptions explicitly before implementing: "Export all or subset?", "Download or Email?", "Which fields?"

---

### Example 2: Simplicity First (Over-abstraction)
**User Request:** "Add a function to calculate discount"

**❌ What LLMs Do (Overengineered)**
Implementing Abstract Base Classes, Strategy Patterns, and Enums for a simple percentage calculation.

**✅ What Should Happen (Simple)**
A simple function: `def calculate_discount(amount, percent): return amount * (percent / 100)`. Only add complexity when actually needed.

---

### Example 3: Surgical Changes (Drive-by Refactoring)
**User Request:** "Fix the bug where empty emails crash the validator"

**❌ What LLMs Do (Too Much)**
Reformatting whitespace, adding docstrings, and "improving" adjacent code like username validation.

**✅ What Should Happen (Surgical)**
Only change the specific lines that fix the reported issue. Match existing style perfectly.

---

### Example 4: Goal-Driven Execution (Verifiable Goals)
**User Request:** "Fix the authentication system"

**❌ What LLMs Do (Vague Approach)**
"I'll review and make improvements." (Proceeds without clear criteria).

**✅ What Should Happen (Verifiable Goals)**
Plan:
1. Write test to reproduce bug.
2. Implement fix.
3. Verify test passes.
4. Verify no regressions.

---

**Key Insight:** Good code is code that solves today's problem simply, not tomorrow's problem prematurely.
