## 2026-05-05 - Home Assistant Config and Options Flow Translation Parity
**Learning:** Home Assistant configuration and options flows render raw unformatted input keys and error codes if `data_description`, `data`, or `error` keys are missing or mismatched in locale translation files (`en.json`, `nl.json`). Both `init` and `user` step keys must maintain exact structural parity across all supported language files.
**Action:** Always check both `en.json` and `nl.json` for key symmetry (`data_description`, error codes, and step keys) and verify options flow schemas against `config_flow.py` when improving integration UI strings.

## 2026-05-05 - Translation File Key Duplication Cleanups
**Learning:** Duplicate key entries in Home Assistant translation JSON files (`en.json`, `nl.json`) cause silent overrides or parsing inconsistencies. When removing duplicates (e.g. duplicate sensor keys or repeated top-level blocks), verify that valid sub-blocks (like `binary_sensor`) are retained and not overwritten by subsequent keys.
**Action:** Always test JSON files using custom `object_pairs_hook` parsing scripts to verify zero duplicate keys and complete key retention across all entities before committing changes.

## 2026-05-05 - Form Selectors and Custom Error Handling in Home Assistant Flows
**Learning:** Setting strict `min`/`max` ranges directly inside `NumberSelectorConfig` causes Home Assistant's `data_entry_flow` to raise an uncaught `InvalidData` schema exception when invalid input is submitted. Omitting `min`/`max` from `NumberSelectorConfig` while validating bounds within the flow step method allows returning a user-friendly form with localized error messages (`errors["base"] = ...`).
**Action:** Rely on python validation logic in flow step methods when specific error keys need to be rendered back to the user, while using `NumberSelectorConfig` with `mode`, `step`, and `unit_of_measurement` for UI formatting.
