# Maintaining translations

The supported language variants are `de`, `en`, `es`, `fr`, `it`, `nl`, `pl`,
`pt`, `pt-BR` and `sv`. English is the complete reference and fallback language.

## Source files

- `custom_components/sonos_follow_me/translations/<language>.json`: Home Assistant
  setup, options, errors, selector choices and entity names/states. Use a language
  code supported by Home Assistant, including the exact `pt-BR` spelling.
- `custom_components/sonos_follow_me/frontend/translations/<language>.json`:
  card-only labels, hints, statuses and editor text.
- `dev/build_card_translations.cjs`: maps shared setting labels and descriptions
  from the integration catalogs into the bundled card. Do not duplicate these
  labels in the card-only catalogs or edit the generated block in the JavaScript.

Custom integrations ship completed `translations/*.json` directly; Home Assistant
does not compile a custom integration's `strings.json`. This project therefore
maintains `translations/en.json` as its English source, with no duplicate
`strings.json`. Write complete strings rather than `[%key:...%]` references.
See [Home Assistant's custom integration translation rules](https://contributors.home-assistant.io/core/integrations/translations/#custom-integrations).

## Editing or adding a language

1. Edit both catalogs for an existing language, or copy both English catalogs
   under the new language code. Keep all keys and placeholders such as `{count}`.
   Translate values only; retain technical identifiers such as `entities`, brand
   names, numeric ranges and the additive TV-offset calculation.
2. Keep `config.step.user` identical to `options.step.init`, and their volume
   steps/errors identical. Selector choices and corresponding entity states must
   use the same text. These repeated values are required as literal strings by
   Home Assistant's custom-integration format; tests check their consistency.
3. Translate all room-count forms (`one`, `few`, `many`, `other`). Unused forms
   can use the ordinary plural. The card selects the form using `Intl.PluralRules`;
   Polish, for example, distinguishes 1, 2 and 5 rooms.
4. Regenerate the bundled card and run the checks:

   ```sh
   npm ci
   npm run build:translations
   npx playwright install chromium
   npm test
   .venv/bin/pytest -q tests/test_translations.py
   ```

5. Commit the two catalogs and the generated JavaScript together. For a new
   language, also update the supported-language lists in both READMEs and here.

The card uses the profile language, then an available base language, then English.
Brazilian Portuguese keeps its own catalog. Translations are bundled into the
existing JavaScript module so loading the card requires no additional language
requests. A language change also refreshes the card and editor.

CI checks exact key coverage, nonempty text, placeholders, supported Home Assistant
language codes, form fields and selector choices. `npm test` verifies that the
generated catalog is current and checks each language's card/editor in a narrow
browser viewport, along with regional fallbacks and Polish plurals. These checks
catch structural and display regressions; native-speaker wording improvements
are welcome through pull requests.

To inspect changes in Home Assistant, restart after updating the catalogs, fully
reload the browser and select the language in your profile. Open a room's
configuration and dashboard card. User-defined room names, speaker names and
entity IDs are not translated by this project.
