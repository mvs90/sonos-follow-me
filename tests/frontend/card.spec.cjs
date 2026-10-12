const { test, expect } = require("@playwright/test");
const path = require("node:path");
const cardScript = path.resolve(
  "custom_components/sonos_follow_me/frontend/sonos-follow-me-card.js",
);
async function setup(page, config = { type: "custom:sonos-follow-me-card" }) {
  await page.route(
    "http://follow-me.test/sonos_follow_me/follow-me-logo.png*",
    (route) =>
      route.fulfill({
        path: path.resolve(
          "custom_components/sonos_follow_me/frontend/follow-me-logo.png",
        ),
        contentType: "image/png",
      }),
  );
  await page.setContent(
    "<base href='http://follow-me.test/'><style>body{margin:20px;background:#eef1f5;font-family:system-ui}sonos-follow-me-card{max-width:460px;--primary-color:#087f83;--primary-text-color:#182c33;--secondary-text-color:#62777c;--divider-color:#dce5e6}</style>",
  );
  await page.addScriptTag({ path: cardScript });
  await page.evaluate((config) => {
    window.calls = [];
    const states = {};
    function state(id, value, attributes = {}) {
      states[id] = { entity_id: id, state: String(value), attributes };
    }
    for (const [room, name, present] of [
      ["bath", "Badezimmer", true],
      ["office", "Arbeitszimmer", false],
    ]) {
      const attr = (setting) => ({ sonos_follow_me_room: room, setting });
      state(`switch.${room}`, "on", {
        ...attr("enabled"),
        room_name: name,
        player: `media_player.${room}`,
        primary: `binary_sensor.${room}_pir`,
        secondary: [`binary_sensor.${room}_radar`],
        sources: ["media_player.living"],
        remembered_volume: 0.4,
        vacant_since: present ? null : Date.now() / 1000 - 600,
      });
      state(
        `binary_sensor.${room}_occupancy`,
        present ? "on" : "off",
        attr("occupancy"),
      );
      state(`switch.${room}_reset`, "on", attr("volume_reset"));
      for (const [key, value, max, step, unit] of [
        ["default_volume", 25, 100, 1, "%"],
        ["volume_cooldown", 30, 10080, 1, "min"],
        ["tv_volume_offset", -10, 100, 1, "pp"],
        ["off_delay", 15, 3600, 1, "s"],
        ["fade_seconds", 3, 30, 0.5, "s"],
      ])
        state(`number.${room}_${key}`, value, {
          ...attr(key),
          min: key === "tv_volume_offset" ? -100 : 0,
          max,
          step,
          unit_of_measurement: unit,
        });
      state(`select.${room}_mode`, "primary", attr("mode"));
      state(`select.${room}_volume_mode`, "room", attr("volume_mode"));
      state(`media_player.${room}`, present ? "playing" : "paused", {
        friendly_name: name,
      });
      state(`binary_sensor.${room}_pir`, "off", { friendly_name: "PIR" });
      state(`binary_sensor.${room}_radar`, present ? "on" : "off", {
        friendly_name: "Radar",
      });
    }
    state("media_player.living", "playing", { friendly_name: "Wohnzimmer" });
    window.hass = {
      states,
      language: "de",
      callService: async (...args) => {
        window.calls.push(args);
        if (window.fail) throw new Error("Keine Berechtigung");
        const [domain, action, data] = args;
        const s = states[data.entity_id];
        if (s) {
          s.state =
            action === "turn_on"
              ? "on"
              : action === "turn_off"
                ? "off"
                : String(data.value ?? data.option ?? s.state);
          card.hass = { ...hass };
        }
      },
    };
    window.card = document.createElement("sonos-follow-me-card");
    card.setConfig(config);
    card.hass = hass;
    document.body.append(card);
  }, config);
}

test("renders a room with only its primary sensor", async ({ page }) => {
  await setup(page, {
    type: "custom:sonos-follow-me-card",
    entities: ["switch.bath"],
  });
  await page.evaluate(() => {
    hass.states["switch.bath"].attributes.secondary = [];
    card.hass = { ...hass };
  });
  await page.getByText("Einstellungen & Sensoren", { exact: true }).click();
  await expect(page.getByText("PIR: Frei", { exact: true })).toBeVisible();
  await expect(page.locator("li").filter({ hasText: "Radar" })).toHaveCount(0);
});

test("following modes hide room-volume controls and restore them without losing values", async ({
  page,
}) => {
  await setup(page, {
    type: "custom:sonos-follow-me-card",
    entities: ["switch.office"],
  });
  await page
    .getByRole("combobox", { name: "Lautstärkequelle", exact: true })
    .selectOption("group");
  await expect(
    page.getByRole("slider", { name: "Standardlautstärke", exact: true }),
  ).toHaveCount(0);
  await expect(page.getByLabel("Abkühlzeit", { exact: true })).toHaveCount(0);
  await expect(
    page.getByLabel("Standardlautstärke verwenden", { exact: true }),
  ).toHaveCount(0);
  await expect(page.getByText(/Abkühlzeit läuft/)).toHaveCount(0);
  await expect(
    page.getByRole("slider", { name: "TV-Offset", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "Lautstärkequelle", exact: true })
    .selectOption("master");
  await expect(page.getByLabel("Abkühlzeit", { exact: true })).toHaveCount(0);
  await page
    .getByRole("combobox", { name: "Lautstärkequelle", exact: true })
    .selectOption("room");
  await expect(
    page.getByRole("slider", { name: "Standardlautstärke", exact: true }),
  ).toHaveValue("25");
  await expect(page.getByLabel("Abkühlzeit", { exact: true })).toHaveValue(
    "30",
  );
});

test("external mode change hides room settings even while a slider has focus", async ({
  page,
}) => {
  await setup(page, {
    type: "custom:sonos-follow-me-card",
    entities: ["switch.bath"],
  });
  await page
    .getByRole("slider", { name: "Standardlautstärke", exact: true })
    .focus();
  await page.evaluate(() => {
    hass.states["select.bath_volume_mode"].state = "master";
    card.hass = { ...hass };
  });
  await expect(
    page.getByRole("slider", { name: "Standardlautstärke", exact: true }),
  ).toHaveCount(0);
});

test("automatically discovers rooms, shows presence and settings", async ({
  page,
}) => {
  await setup(page);
  await expect(page.getByText("Badezimmer", { exact: true })).toBeVisible();
  await expect(page.getByText("Arbeitszimmer", { exact: true })).toBeVisible();
  await expect(page.getByText("Belegt", { exact: true })).toBeVisible();
  await expect(
    page
      .getByRole("slider", { name: "Standardlautstärke", exact: true })
      .first(),
  ).toHaveValue("25");
  await expect(page.getByText("TV-Offset (%)").first()).toBeVisible();
  await expect(page.getByText("TV-Offset (pp)")).toHaveCount(0);
  await expect(
    page.getByLabel("Abkühlzeit", { exact: true }).first(),
  ).toHaveAccessibleDescription(
    /Nach Ablauf wird bei der nächsten Bewegung auf die Standardlautstärke eingeblendet/,
  );
  await expect(page.getByText("Abkühlzeit läuft: 20 min")).toBeVisible();
  await page
    .locator("sonos-follow-me-card")
    .screenshot({ path: "test-results/card-desktop.png" });
});

test("controls send standard Home Assistant service calls", async ({
  page,
}) => {
  await setup(page, {
    type: "custom:sonos-follow-me-card",
    entities: ["switch.bath"],
  });
  const volume = page.getByRole("slider", {
    name: "Standardlautstärke",
    exact: true,
  });
  await volume.press("ArrowRight");
  await expect
    .poll(() => page.evaluate(() => window.calls))
    .toContainEqual([
      "number",
      "set_value",
      { entity_id: "number.bath_default_volume", value: 26 },
    ]);
  await expect(volume).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(volume).toHaveValue("27");
  await expect(page.getByText("27 %", { exact: true })).toBeVisible();
  await page.getByLabel("Follow Me", { exact: true }).uncheck();
  await expect
    .poll(() => page.evaluate(() => window.calls))
    .toContainEqual(["switch", "turn_off", { entity_id: "switch.bath" }]);
  await page.getByText("Einstellungen & Sensoren").click();
  await page.getByLabel("Sensorlogik").selectOption("equal");
  await expect
    .poll(() => page.evaluate(() => window.calls))
    .toContainEqual([
      "select",
      "select_option",
      { entity_id: "select.bath_mode", option: "equal" },
    ]);
});

test("renders permission errors and rejects out of range input", async ({
  page,
}) => {
  await setup(page, { entities: ["switch.bath"] });
  await page.getByLabel("Abkühlzeit", { exact: true }).fill("10081");
  await page.getByLabel("Abkühlzeit", { exact: true }).press("Tab");
  expect(await page.evaluate(() => window.calls.length)).toBe(0);
  await page.evaluate(() => (window.fail = true));
  await page.getByLabel("Follow Me", { exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Keine Berechtigung");
});

test("unavailable entities and missing rooms remain readable", async ({
  page,
}) => {
  await setup(page, { entities: ["switch.bath", "switch.deleted"] });
  await page.evaluate(() => {
    hass.states["number.bath_default_volume"].state = "unavailable";
    card.hass = hass;
  });
  await expect(
    page.getByLabel("Standardlautstärke", { exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByText("Raum nicht verfügbar", { exact: true }),
  ).toBeVisible();
});

test("safe names, mobile layout and live updates preserve typed inputs", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 900 });
  await setup(page, { entities: ["switch.bath"] });
  await page.evaluate(() => {
    hass.states["switch.bath"].attributes.room_name =
      "<img src=x onerror=alert(1)>";
    card.hass = hass;
  });
  await expect(
    page.getByText("<img src=x onerror=alert(1)>", { exact: true }),
  ).toBeVisible();
  expect(await page.locator("img").count()).toBe(1);
  expect(
    await page.locator("img.logo").evaluate((image) => image.naturalWidth),
  ).toBeGreaterThan(0);
  const input = page.getByLabel("Abkühlzeit", { exact: true });
  await input.fill("45");
  await page.evaluate(() => {
    card.hass = { ...hass };
  });
  await expect(input).toHaveValue("45");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(
    360,
  );
  await page.screenshot({
    path: "test-results/card-mobile.png",
    fullPage: true,
  });
});

test("card editor emits selected rooms and custom card is registered", async ({
  page,
}) => {
  await setup(page);
  await page.evaluate(() => {
    const editor = customElements
      .get("sonos-follow-me-card")
      .getConfigElement();
    editor.setConfig({ type: "custom:sonos-follow-me-card" });
    editor.hass = hass;
    editor.addEventListener(
      "config-changed",
      (e) => (window.edited = e.detail.config),
    );
    document.body.replaceChildren(editor);
  });
  await page.getByText("Badezimmer", { exact: true }).click();
  await expect
    .poll(() => page.evaluate(() => window.edited.entities))
    .toEqual(["switch.bath"]);
  expect(await page.evaluate(() => window.customCards[0].type)).toBe(
    "sonos-follow-me-card",
  );
});

test("TV offset accepts negative values and shows active target", async ({
  page,
}) => {
  await setup(page, { entities: ["switch.bath"] });
  await page.evaluate(() => {
    hass.states["switch.bath"].attributes.tv_volume_active = true;
    hass.states["switch.bath"].attributes.playback_target_volume = 0.15;
    card.hass = { ...hass };
  });
  await expect(page.getByText("TV-Lautstärke aktiv: 15 %")).toBeVisible();
  const offset = page.getByRole("slider", { name: "TV-Offset", exact: true });
  await offset.press("ArrowLeft");
  await expect
    .poll(() => page.evaluate(() => window.calls))
    .toContainEqual([
      "number",
      "set_value",
      { entity_id: "number.bath_tv_volume_offset", value: -11 },
    ]);
  await expect(page.getByText("-11 %", { exact: true })).toBeVisible();
  await offset.press("End");
  await expect(offset).toHaveValue("100");
  await expect(page.getByText("+100 %", { exact: true })).toBeVisible();
  await offset.press("Home");
  await expect(offset).toHaveValue("-100");
});

test("slider previews changes during drag and commits once on release", async ({
  page,
}) => {
  await setup(page, { entities: ["switch.bath"] });
  const slider = page.getByRole("slider", {
    name: "Standardlautstärke",
    exact: true,
  });
  const box = await slider.boundingBox();
  await page.mouse.move(box.x + box.width * 0.25, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.7, box.y + box.height / 2, {
    steps: 8,
  });
  const preview = await slider.inputValue();
  expect(Number(preview)).toBeGreaterThan(60);
  await expect(page.getByText(`${preview} %`, { exact: true })).toBeVisible();
  expect(await page.evaluate(() => window.calls.length)).toBe(0);
  await page.evaluate(() => {
    card.hass = { ...hass };
  });
  await expect(slider).toHaveValue(preview);
  await page.mouse.up();
  await expect
    .poll(() => page.evaluate(() => window.calls))
    .toEqual([
      [
        "number",
        "set_value",
        { entity_id: "number.bath_default_volume", value: Number(preview) },
      ],
    ]);
});

test("focused slider receives delayed Home Assistant state confirmation", async ({
  page,
}) => {
  await setup(page, { entities: ["switch.bath"] });
  await page.evaluate(() => {
    hass.callService = async (domain, action, data) => {
      window.calls.push([domain, action, data]);
      setTimeout(() => {
        hass.states[data.entity_id] = {
          ...hass.states[data.entity_id],
          state: String(data.value),
        };
        card.hass = { ...hass };
      }, 150);
    };
  });
  const offset = page.getByRole("slider", { name: "TV-Offset", exact: true });
  await offset.press("ArrowLeft");
  await expect(offset).toBeFocused();
  await expect(offset).toHaveValue("-11");
  await expect(page.getByText("-11 %", { exact: true })).toBeVisible();
});
