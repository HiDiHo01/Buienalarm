# Localization Guide

This document describes how to maintain translations for the Buienalarm Home Assistant integration.

## Current languages and files

Translations are stored in `custom_components/buienalarm/translations/`:

- `en.json` — English.
- `nl.json` — Dutch.

These are Home Assistant integration translation files. Keep translation keys and JSON structure compatible across supported languages. Do not place user-facing integration translations in README or Python source when they belong in these files.

## What to translate

The translation files currently contain strings for:

- The integration title and configuration flow.
- Configuration errors and abort reasons.
- Options flow labels, descriptions, and validation errors.
- Sensor names under `entity.sensor`.
- Binary sensor names under `entity.binary_sensor`.

When adding or changing a user-facing label, first determine whether it is supplied by Home Assistant's translation system or explicitly defined by the integration. Follow the existing implementation and translation-key conventions.

## Translation workflow

1. **Identify the source key.** Inspect the relevant config-flow or options-flow code, entity description, and existing translation file. For entity names, check the entity's `translation_key` and key definitions in the integration; do not assume the Python class name is the translation key.
2. **Update every supported locale.** Add or update the same logical key in both `en.json` and `nl.json`. Preserve the existing JSON nesting and key names. Translate the displayed text, not the key.
3. **Keep locale structures aligned.** Do not remove keys from one locale while leaving them in another. In particular, configuration-flow and options-flow labels, descriptions, and error keys must retain matching key sets.
4. **Use natural, consistent wording.** English text belongs in `en.json`; Dutch text belongs in `nl.json`. Preserve the meaning of the source text, including validation rules, units, and technical distinctions. Use the same terminology for the same concept throughout the integration.
5. **Preserve formatting and placeholders.** Keep JSON valid, retain any required placeholders exactly, and do not change a key's meaning as a way to improve its wording.
6. **Review the result.** Check the diff for missing keys, accidental key renames, inconsistent terminology, and unrelated changes.

## Naming and terminology

- Keep translation keys stable. Renaming a key can affect how Home Assistant resolves an entity's translated name.
- For entity translations, ensure the key matches the entity's effective `translation_key` (or the established key convention used by that entity).
- Keep sensor and binary sensor names concise and suitable for Home Assistant's UI.
- Keep units and technical meaning accurate. For example, precipitation intensity is a rate and is typically expressed in `mm/h`; do not translate it as accumulated rainfall in millimetres.
- Do not translate identifiers, entity IDs, Python symbols, JSON keys, or API field names unless the code explicitly treats them as user-facing text.

## Validation

Run the focused translation tests from the repository root:

```bash
pytest tests/test_translations.py
```

These tests check that the supported translation files exist and contain valid JSON, that expected sections and entity names are present, and that selected configuration/options keys remain aligned between English and Dutch.

For broader changes, run the full test suite as described in [CONTRIBUTING.md](CONTRIBUTING.md):

```bash
pytest
```

A passing structural test does not prove that a translation is linguistically correct or that every UI path has been manually verified. Review the translated strings in context as part of the pull request.

## Pull request checklist

Before submitting a localization change:

- [ ] Updated all affected supported locales (`en.json` and `nl.json`).
- [ ] Preserved JSON structure and translation keys.
- [ ] Checked configuration-flow and options-flow key parity where relevant.
- [ ] Checked sensor and binary sensor translation keys against the implementation.
- [ ] Ran `pytest tests/test_translations.py` and recorded the actual result.
- [ ] Reviewed spelling, grammar, terminology, units, and placeholders.
- [ ] Kept the change focused and described any locale or key intentionally added or removed.
