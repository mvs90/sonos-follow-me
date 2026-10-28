/* Generate the bundled card's text catalog from editable JSON translations. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const prettier = require("prettier");
const root = path.resolve(__dirname, "../custom_components/sonos_follow_me");
const cardPath = path.join(root, "frontend/sonos-follow-me-card.js");
const startMarker = "  // BEGIN GENERATED TRANSLATIONS";
const endMarker = "  // END GENERATED TRANSLATIONS";
const shared = {
  volume_mode: "entity.select.volume_mode.name",
  room: "selector.volume_mode.options.room",
  group: "selector.volume_mode.options.group",
  master: "selector.volume_mode.options.master",
  default_volume: "entity.number.default_volume.name",
  volume_cooldown: "entity.number.volume_cooldown.name",
  off_delay: "entity.number.off_delay.name",
  fade_seconds: "entity.number.fade_seconds.name",
  volume_reset: "entity.switch.volume_reset.name",
  mode: "entity.select.mode.name",
  primary: "selector.mode.options.primary",
  equal: "selector.mode.options.equal",
  tv_hint: "config.step.user.data_description.tv_volume_offset",
  follow_hint: "config.step.user.data_description.volume_mode",
};
function readCatalogs(dir) {
  return Object.fromEntries(
    fs
      .readdirSync(dir)
      .filter((name) => name.endsWith(".json"))
      .sort()
      .map((name) => [
        name.slice(0, -5),
        JSON.parse(fs.readFileSync(path.join(dir, name), "utf8")),
      ]),
  );
}
function leaves(obj, prefix = "") {
  return Object.fromEntries(
    Object.entries(obj).flatMap(([key, value]) => {
      const name = prefix ? `${prefix}.${key}` : key;
      return typeof value === "object" && value !== null
        ? Object.entries(leaves(value, name))
        : [[name, value]];
    }),
  );
}
function validate(catalogs, label) {
  const baseline = leaves(catalogs.en);
  for (const [locale, catalog] of Object.entries(catalogs)) {
    const texts = leaves(catalog);
    assert.deepEqual(
      Object.keys(texts).sort(),
      Object.keys(baseline).sort(),
      `${label}: keys differ for ${locale}`,
    );
    for (const [key, value] of Object.entries(texts)) {
      assert.ok(
        typeof value === "string" && value.trim(),
        `${label}: empty text ${locale}.${key}`,
      );
      const placeholders = (text) =>
        [...text.matchAll(/\{\w+\}/g)].map((match) => match[0]).sort();
      assert.deepEqual(
        placeholders(value),
        placeholders(baseline[key]),
        `${label}: placeholders differ for ${locale}.${key}`,
      );
    }
  }
}
async function main() {
  const integration = readCatalogs(path.join(root, "translations"));
  const frontend = readCatalogs(path.join(root, "frontend/translations"));
  assert.deepEqual(
    Object.keys(frontend),
    Object.keys(integration),
    "Integration and card must support the same languages",
  );
  validate(integration, "integration");
  validate(frontend, "card");
  const words = {};
  for (const [locale, catalog] of Object.entries(frontend)) {
    const backend = leaves(integration[locale]);
    for (const key of Object.keys(shared))
      assert.ok(
        !(key in catalog),
        `Maintain shared setting ${key} only in the integration catalog`,
      );
    words[locale] = {
      ...catalog,
      ...Object.fromEntries(
        Object.entries(shared).map(([key, source]) => {
          assert.ok(backend[source], `Missing shared text ${locale}.${source}`);
          return [key, backend[source]];
        }),
      ),
    };
  }
  const current = fs.readFileSync(cardPath, "utf8");
  const start = current.indexOf(startMarker),
    end = current.indexOf(endMarker);
  assert.ok(start >= 0 && end > start, "Missing generated translation markers");
  const updated = await prettier.format(
    current.slice(0, start) +
      startMarker +
      "\n  const words = " +
      JSON.stringify(words, null, 2) +
      ";\n" +
      current.slice(end),
    { filepath: cardPath },
  );
  if (process.argv.includes("--check")) {
    assert.equal(
      updated,
      current,
      "Bundled translations are stale. Run npm run build:translations and commit the card.",
    );
  } else fs.writeFileSync(cardPath, updated);
  console.log(
    `Validated ${Object.keys(words).length} languages; shared labels come from Home Assistant translations.`,
  );
}
main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
