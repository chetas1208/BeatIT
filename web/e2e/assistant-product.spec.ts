import { test, expect } from "@playwright/test";

const apiBase = process.env.PLAYWRIGHT_API_BASE ?? "http://127.0.0.1:8000/api/v1";

test.describe("BeatIT Copilot product spine", () => {
  test.beforeEach(async ({ request }) => {
    const health = await request.get(`${apiBase}/health`);
    test.skip(!health.ok(), "Backend not running — start uvicorn on :8000");
  });

  test("unified copilot opens and accepts a message", async ({ page }) => {
    await page.goto("/");
    const trigger = page.getByRole("button", { name: /beatit copilot/i });
    await expect(trigger).toBeVisible();
    await trigger.click();
    const dialog = page.getByRole("dialog", { name: /beatit copilot/i });
    await expect(dialog).toBeVisible();
    const input = page.getByRole("textbox", { name: /message beatit copilot/i });
    await input.fill("What is educational simulation-only output?");
    await page.getByRole("button", { name: /send message/i }).click();
    await expect(dialog.getByRole("log")).toContainText(/simulation|clarify|BeatIT/i, {
      timeout: 45_000,
    });
  });

  test("backend assistant API supports ensemble shadow trial turn", async ({ request }) => {
    const ensembleResp = await request.post(`${apiBase}/twin/ensemble`, {
      data: {
        origin_snapshot_id: "pw-snap",
        seed: 7,
        sample_count: 4,
        origin_quality: "observed",
        state: {
          case_id: "pw-case",
          created_at: "2026-01-01T00:00:00",
          measurements: {
            heart_rate_bpm: { value: 72, unit: "bpm", source: "file_extraction", confidence: 1 },
            systolic_bp_mmhg: { value: 120, unit: "mmHg", source: "file_extraction", confidence: 1 },
            diastolic_bp_mmhg: { value: 80, unit: "mmHg", source: "file_extraction", confidence: 1 },
            edv_ml: { value: 120, unit: "mL", source: "file_extraction", confidence: 1 },
            esv_ml: { value: 70, unit: "mL", source: "file_extraction", confidence: 1 },
          },
          hemodynamics: {
            preload_index: { value: 1, unit: "index", source: "file_extraction", confidence: 1 },
            afterload_index: { value: 1, unit: "index", source: "file_extraction", confidence: 1 },
            contractility_index: { value: 1, unit: "index", source: "file_extraction", confidence: 1 },
            systemic_vascular_resistance_index: {
              value: 1,
              unit: "index",
              source: "file_extraction",
              confidence: 1,
            },
          },
        },
        distributions: [
          {
            parameter_id: "heart_rate_bpm",
            family: "normal",
            parameters: { mean: 72, sd: 2 },
            bounds: { min: 30, max: 200 },
            source: "measurement",
            evidence_ids: ["pw.json"],
            rationale: "playwright",
            version: "v1",
          },
        ],
      },
    });
    test.skip(!ensembleResp.ok(), "Could not create ensemble fixture");
    const ensemble = await ensembleResp.json();
    const msg = await request.post(`${apiBase}/assistant/message`, {
      data: {
        conversation_id: "pw-conv-1",
        message: "Run a shadow trial on this ensemble.",
        context: {
          conversation_id: "pw-conv-1",
          audience: "physician",
          ensemble_id: ensemble.id,
        },
      },
    });
    expect(msg.ok()).toBeTruthy();
    const body = await msg.json();
    expect(body.safety_disclaimer).toBeTruthy();
    expect(body.trace.tools_invoked).toContain("run_shadow_trial");
  });

  test("backend assistant API supports missing piece turn", async ({ request }) => {
    const ensembleResp = await request.post(`${apiBase}/twin/ensemble`, {
      data: {
        origin_snapshot_id: "pw-snap-mp",
        seed: 9,
        sample_count: 4,
        origin_quality: "observed",
        state: {
          case_id: "pw-case-mp",
          created_at: "2026-01-01T00:00:00",
          measurements: {
            heart_rate_bpm: { value: 72, unit: "bpm", source: "file_extraction", confidence: 1 },
            systolic_bp_mmhg: { value: 120, unit: "mmHg", source: "file_extraction", confidence: 1 },
            diastolic_bp_mmhg: { value: 80, unit: "mmHg", source: "file_extraction", confidence: 1 },
            edv_ml: { value: 120, unit: "mL", source: "file_extraction", confidence: 1 },
            esv_ml: { value: 70, unit: "mL", source: "file_extraction", confidence: 1 },
          },
          hemodynamics: {
            preload_index: { value: 1, unit: "index", source: "file_extraction", confidence: 1 },
            afterload_index: { value: 1, unit: "index", source: "file_extraction", confidence: 1 },
            contractility_index: { value: 1, unit: "index", source: "file_extraction", confidence: 1 },
            systemic_vascular_resistance_index: {
              value: 1,
              unit: "index",
              source: "file_extraction",
              confidence: 1,
            },
          },
        },
        distributions: [
          {
            parameter_id: "heart_rate_bpm",
            family: "normal",
            parameters: { mean: 72, sd: 2 },
            bounds: { min: 30, max: 200 },
            source: "measurement",
            evidence_ids: ["pw-mp.json"],
            rationale: "playwright",
            version: "v1",
          },
        ],
      },
    });
    test.skip(!ensembleResp.ok(), "Could not create ensemble fixture");
    const ensemble = await ensembleResp.json();
    const msg = await request.post(`${apiBase}/assistant/message`, {
      data: {
        conversation_id: "pw-conv-mp",
        message: "Run the missing piece analysis for uncertainty.",
        context: {
          conversation_id: "pw-conv-mp",
          audience: "physician",
          ensemble_id: ensemble.id,
        },
      },
    });
    expect(msg.ok()).toBeTruthy();
    const body = await msg.json();
    expect(body.safety_disclaimer).toBeTruthy();
    expect(body.trace.tools_invoked).toContain("run_missing_piece");
  });
});
