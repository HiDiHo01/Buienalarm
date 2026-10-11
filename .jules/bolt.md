# Bolt's Performance Journal

Critical learnings on performance optimizations for this repository.
## 2026-05-05 - Avoid Duplicate Formatting in Home Assistant State Evaluation
**Learning:** Computing Home Assistant sensor states using methods that format rich attribute objects (e.g. `get_precipitation_periods_as_dict()`) causes duplicate timestamp parsing and ISO string serialization overhead when evaluating condition checks or counts.
**Action:** When evaluating numerical properties or counts for sensors, query raw internal lists or counts directly (e.g. `len(self._get_precipitation_periods())`) rather than invoking attribute formatting helpers that build complex dictionaries.
