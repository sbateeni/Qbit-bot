# Qbit-Bot Engineering Standards (CLAUDE.md)

Derived from Karpathy's principles for robust AI-driven development.

## 1. Principles
- **Simplicity First**: Minimize code. No over-engineering. If a simple loop works, don't use complex event emitters.
- **Data-Driven**: Always log the state of data. If it fails, we need to see the raw input.
- **Surgical Changes**: Only modify what is broken or strictly necessary. No "aesthetic" refactoring.
- **Fail-Safe & Self-Healing**: Every critical failure must trigger a system snapshot.
- **Zero Ambiguity**: No silent assumptions. Errors must be loud and documented.

## 2. Technical Stack & Conventions
- **Language**: Python 3.10+
- **Type Safety**: Use Pydantic models for all external data (API, MT5 results).
- **Communication**: Use `QbitBot` parent logger. Hierarchy: `QbitBot.Engine`, `QbitBot.Executor`.
- **Trading Safety**: Always call `mt5_mgr.check_connection()` before any trade.
- **Verification**: Use `SnapshotManager` to audit system state periodically and on failure.

## 3. Workflow
- **Plan**: Describe what you will change before writing code.
- **Build**: Implement minimal robust solution.
- **Verify**: Use logs and snapshots to confirm success.
- **Clean**: Remove unused imports or debug statements.

## 4. Operational Commands
- **Run Bot**: `python run_bot.py`
- **Dashboard**: `npm run dev` (in dashboard folder)
- **Snapshot**: `python -c "from brain.snapshot_manager import SnapshotManager; SnapshotManager.capture_full_state()"`
- **Aggregated Code**: `PowerShell Script provided in root`
