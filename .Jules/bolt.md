# Bolt's Journal - Critical Learnings

## 2026-05-18 - Avoid datetime object creation in hot data loops
**Learning:** In Home Assistant integrations processing timeseries data (such as Buienalarm's 5-minute precipitation forecast bins), converting epoch timestamps to `datetime` objects inside loops for time comparison operations (like checking if `timestamp < current_time < timestamp + 300`) incurs significant CPU overhead (up to ~6.5x slower). Comparing numeric epoch floats/ints directly bypasses Python datetime object construction, timezone resolution, and timedelta arithmetic.
**Action:** Always compare numeric epoch timestamps (`ts <= now_ts < ts + 300`) in data processing loops, and only convert to `datetime` objects when formatting strings or returning actual `datetime` instances.
