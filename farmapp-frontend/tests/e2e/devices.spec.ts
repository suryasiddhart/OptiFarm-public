import { test, expect, type Page, type APIRequestContext } from "@playwright/test";
import { cellOrigin, heatmapLayout } from "../../src/utils/heatmapLayout";

/**
 * FarmApp E2E — devices on My Fields and the Live View popup.
 *
 * Needs the backend (e.g. docker-compose.ingest.yml) behind the dev server's
 * /api proxy. The user and field are created through the API; the session is
 * put into localStorage the same way the app stores it after login.
 */

const PASSWORD = "e2e-Passw0rd";

async function signIn(page: Page, request: APIRequestContext) {
  const mobileno = `6${Date.now().toString().slice(-9)}`;
  await request.post("/api/auth/register", {
    data: { firstname: "E2E", lastname: "Devices", mobileno, password: PASSWORD },
  });
  const login = await (await request.post("/api/auth/login", { data: { mobileno, password: PASSWORD } })).json();
  const auth = { Authorization: `Bearer ${login.access_token}` };
  // 1 m x 1 m at 0.2 m spacing → a 5 x 5 grid
  const field = await (
    await request.post("/api/fields/", {
      headers: auth,
      data: {
        fieldlength: 1, fieldbreadth: 1, croptype: "rice", cropsubtype: "e2e", cropinterval: 0.2,
        fieldlat: 10, fieldlong: 76,
      },
    })
  ).json();
  await page.addInitScript(([token, user]) => {
    localStorage.setItem("access_token", token);
    localStorage.setItem("user", user);
  }, [login.access_token, JSON.stringify(login.user)] as const);
  return field as { fieldid: number };
}

const fieldRow = (page: Page, fieldId: number) =>
  page.getByRole("row").filter({ has: page.getByRole("cell", { name: String(fieldId), exact: true }) });

test.describe("Devices and Live View", () => {
  test("sidebar only has My Fields and Logout", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("/fields");
    const menu = page.getByRole("menu");
    await expect(menu.getByRole("menuitem")).toHaveText(["My Fields", "Logout"]);
  });

  test("add, rotate and delete a device; passkey shown only once", async ({ page, request }) => {
    const field = await signIn(page, request);
    await page.goto("/fields");
    const row = fieldRow(page, field.fieldid);
    await expect(row.getByTestId("device-count")).toHaveText("0");

    await row.getByRole("button", { name: "View devices" }).click();
    const devices = page.getByRole("dialog", { name: /Devices — Field/ });
    await devices.getByRole("button", { name: "Add device" }).click();

    const add = page.getByRole("dialog", { name: /Add device/ });
    await add.getByLabel("Device name").fill("North corner sensor");
    await add.getByRole("button", { name: "Add device" }).click();

    // Passkey popup: shown once, with the generated device ID
    const shown = page.getByRole("dialog", { name: "Device added" });
    await expect(shown).toContainText("This passkey is shown only once.");
    const passkey = (await shown.getByTestId("device-passkey").textContent())!.trim();
    expect(passkey.length).toBeGreaterThanOrEqual(40);
    await shown.getByRole("button", { name: "I've saved the passkey" }).click();
    await expect(shown).toBeHidden();
    await expect(page.locator("body")).not.toContainText(passkey); // gone from the page

    await expect(devices.getByRole("cell", { name: "North corner sensor" })).toBeVisible();
    await expect(row.getByTestId("device-count")).toHaveText("1");

    // Rotate: a new, different passkey is shown once
    await devices.getByRole("button", { name: "Rotate passkey" }).click();
    await page.locator(".ant-popover").getByRole("button", { name: "Rotate" }).click();
    const rotated = page.getByRole("dialog", { name: "Passkey rotated" });
    const newPasskey = (await rotated.getByTestId("device-passkey").textContent())!.trim();
    expect(newPasskey).not.toBe(passkey);
    await rotated.getByRole("button", { name: "I've saved the passkey" }).click();

    // Delete: removed from the list and from the count
    await devices.getByRole("button", { name: "Delete" }).click();
    await page.locator(".ant-popover").getByRole("button", { name: "Delete" }).click();
    await expect(devices.getByText("No devices on this field yet.")).toBeVisible();
    await devices.getByRole("button", { name: "Close" }).last().click();
    await expect(row.getByTestId("device-count")).toHaveText("0");
  });

  test("Live View popup places m2_5 at row 2, column 5", async ({ page, request }) => {
    const field = await signIn(page, request);
    let readingRequests = 0;
    await page.route(`**/api/moisture/field/${field.fieldid}*`, (route) => {
      readingRequests += 1;
      return route.fulfill({
        json: [{
          moisture: { m2_5: 42, m1_1: 18.5 }, rtctime: new Date().toISOString(),
          deviceid: "dev-e2e", userinfo: 1, fieldid: field.fieldid,
        }],
      });
    });
    await page.goto("/fields");
    await fieldRow(page, field.fieldid).getByRole("button", { name: "Live View" }).click();

    const live = page.getByRole("dialog", { name: /Live View — Field/ });
    const canvas = live.getByTestId("moisture-heatmap");
    await expect(canvas).toBeVisible();
    await expect(live).toContainText("5 × 5");

    // Hover the centre of row 2, column 5 (zero-based 1, 4)
    const layout = heatmapLayout(5, 5);
    const { x, y } = cellOrigin(layout, 1, 4);
    await canvas.hover({ position: { x: x + layout.cellSize / 2, y: y + layout.cellSize / 2 } });
    const tooltip = live.getByTestId("moisture-heatmap-tooltip");
    await expect(tooltip).toContainText("m2_5");
    await expect(tooltip).toContainText("row 2, column 5");
    await expect(tooltip).toContainText("Moisture: 42%");

    // Close stops the popup (and its polling)
    await live.getByRole("button", { name: "Close" }).last().click();
    await expect(live).toBeHidden();
    const afterClose = readingRequests;
    await page.waitForTimeout(16000);
    expect(readingRequests).toBe(afterClose);
  });
});
