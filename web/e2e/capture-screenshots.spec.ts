import { test } from "@playwright/test";
import path from "node:path";

const outDir = path.join(__dirname, "../../docs/screenshots");

test.describe("capture live UI", () => {
  test("save console screenshots", async ({ page }) => {
    test.setTimeout(120_000);

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.addInitScript(() => {
      localStorage.setItem("hearttwin:disclaimer-ack:v1", "1");
    });

    await page.goto("/twin", { waitUntil: "domcontentloaded" });
    await page.evaluate(() => {
      localStorage.setItem("hearttwin:disclaimer-ack:v1", "1");
      document.querySelector('[role="dialog"][aria-labelledby="ht-disclaimer-title"]')?.remove();
    });
    await page.getByText("BeatIT", { exact: true }).first().waitFor({ state: "visible", timeout: 30_000 });
    await page.waitForTimeout(3000);
    await page.screenshot({
      path: path.join(outDir, "01-twin-console.png"),
      fullPage: true,
    });

    const copilot = page.getByRole("button", { name: /open beatit copilot/i });
    if (await copilot.isVisible({ timeout: 5000 }).catch(() => false)) {
      await copilot.click();
      await page.waitForTimeout(1500);
      await page.screenshot({
        path: path.join(outDir, "02-beatit-copilot-open.png"),
        fullPage: true,
      });
    }

    await page.goto("/experiment", { waitUntil: "domcontentloaded" });
    await page.evaluate(() => {
      document.querySelector('[role="dialog"][aria-labelledby="ht-disclaimer-title"]')?.remove();
    });
    await page.waitForTimeout(4000);
    await page.screenshot({
      path: path.join(outDir, "03-experiment-mode.png"),
      fullPage: true,
    });

    await page.goto("/evidence", { waitUntil: "domcontentloaded" });
    await page.evaluate(() => {
      document.querySelector('[role="dialog"][aria-labelledby="ht-disclaimer-title"]')?.remove();
    });
    await page.waitForTimeout(4000);
    await page.screenshot({
      path: path.join(outDir, "04-evidence-mode.png"),
      fullPage: true,
    });
  });
});
