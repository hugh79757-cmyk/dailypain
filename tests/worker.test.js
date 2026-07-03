/**
 * Worker unit tests — direct module import with mocked env.DB bindings.
 * No miniflare or dev server required.
 */
import { describe, it, expect, beforeEach } from "vitest";
import worker from "../workers/worker.js";

/**
 * Creates a mock D1 binding with spy-able .prepare().bind().run()/.all() chain.
 * Returns { db, history } where history tracks all calls.
 */
function createMockDB() {
    const history = { prepare: [], bind: [], run: [], all: [] };
        const db = {
            prepare(sql) {
                history.prepare.push(sql);
                const stmt = { _sql: sql };
                stmt.all = async () => {
                    history.all.push({ sql: stmt._sql, args: [] });
                    return { results: [] };
                };
                stmt.bind = (...args) => {
                    history.bind.push(args);
                    const bound = { _sql: sql, _args: args };
                    bound.run = async () => {
                        history.run.push({ sql: bound._sql, args: bound._args });
                        return { success: true };
                    };
                    bound.all = async () => {
                        history.all.push({ sql: bound._sql, args: bound._args });
                        return { results: [] };
                    };
                    return bound;
                };
                return stmt;
            }
        };
    return { db, history };
}

describe("Worker routes", () => {
    let env;

    beforeEach(() => {
        const { db, history } = createMockDB();
        env = { DB: db, API_TOKEN: "test-token" };
    });

    // ── OPTIONS ──
    it("OPTIONS returns 200 with CORS headers for known origin", async () => {
        const req = new Request("https://dailypain.hugh79757.workers.dev/api/pains", {
            method: "OPTIONS",
            headers: { Origin: "https://dailypain.hugh79757.workers.dev" },
        });
        const res = await worker.fetch(req, env);
        expect(res.status).toBe(200);
        expect(res.headers.get("Access-Control-Allow-Origin")).toBe("https://dailypain.hugh79757.workers.dev");
    });

    it("OPTIONS returns 200 without CORS for unknown origin", async () => {
        const req = new Request("https://dailypain.hugh79757.workers.dev/api/pains", {
            method: "OPTIONS",
            headers: { Origin: "https://evil.com" },
        });
        const res = await worker.fetch(req, env);
        expect(res.status).toBe(200);
        expect(res.headers.get("Access-Control-Allow-Origin")).toBeNull();
    });

    // ── POST /api/pain auth ──
    it("POST /api/pain without auth returns 401", async () => {
        const req = new Request("https://dailypain.hugh79757.workers.dev/api/pain", {
            method: "POST",
            body: JSON.stringify({ date: "2026-01-01" }),
            headers: { "Content-Type": "application/json" },
        });
        const res = await worker.fetch(req, env);
        expect(res.status).toBe(401);
        const body = await res.json();
        expect(body.error).toBe("Unauthorized");
    });

    it("POST /api/pain with wrong auth returns 401", async () => {
        const req = new Request("https://dailypain.hugh79757.workers.dev/api/pain", {
            method: "POST",
            body: JSON.stringify({ date: "2026-01-01" }),
            headers: { "Content-Type": "application/json", Authorization: "Bearer wrong-token" },
        });
        const res = await worker.fetch(req, env);
        expect(res.status).toBe(401);
    });

    it("POST /api/pain with valid auth returns 200", async () => {
        const req = new Request("https://dailypain.hugh79757.workers.dev/api/pain", {
            method: "POST",
            body: JSON.stringify({
                date: "2026-01-01",
                keyword: "세금 신고",
                category: "세무회계",
                title: "부가세 신고 방법",
                description: "복잡해요",
                pain_summary: "부가세 어려움",
                pain_score: 85,
                solution_hint: "자동화",
                source_url: "https://kin.naver.com/q1",
                source: "naver_kin",
            }),
            headers: { "Content-Type": "application/json", Authorization: "Bearer test-token" },
        });
        const res = await worker.fetch(req, env);
        expect(res.status).toBe(200);
        const body = await res.json();
        expect(body.ok).toBe(true);
    });

    // ── GET /api/pains ──
    it("GET /api/pains returns JSON array", async () => {
        const req = new Request("https://dailypain.hugh79757.workers.dev/api/pains?date=2026-01-01");
        const res = await worker.fetch(req, env);
        expect(res.status).toBe(200);
        expect(res.headers.get("Content-Type")).toContain("application/json");
        const body = await res.json();
        expect(Array.isArray(body)).toBe(true);
    });

    // ── GET /api/dates ──
    it("GET /api/dates returns array of date strings", async () => {
        const req = new Request("https://dailypain.hugh79757.workers.dev/api/dates");
        const res = await worker.fetch(req, env);
        expect(res.status).toBe(200);
        const body = await res.json();
        expect(Array.isArray(body)).toBe(true);
    });

    // ── POST /api/star auth ──
    it("POST /api/star without auth returns 401", async () => {
        const req = new Request("https://dailypain.hugh79757.workers.dev/api/star", {
            method: "POST",
            body: JSON.stringify({ id: 1 }),
            headers: { "Content-Type": "application/json" },
        });
        const res = await worker.fetch(req, env);
        expect(res.status).toBe(401);
    });

    it("POST /api/star with auth returns 200", async () => {
        const req = new Request("https://dailypain.hugh79757.workers.dev/api/star", {
            method: "POST",
            body: JSON.stringify({ id: 1 }),
            headers: { "Content-Type": "application/json", Authorization: "Bearer test-token" },
        });
        const res = await worker.fetch(req, env);
        expect(res.status).toBe(200);
        const body = await res.json();
        expect(body.ok).toBe(true);
    });

    // ── GET /api/starred ──
    it("GET /api/starred returns JSON array", async () => {
        const req = new Request("https://dailypain.hugh79757.workers.dev/api/starred");
        const res = await worker.fetch(req, env);
        expect(res.status).toBe(200);
        const body = await res.json();
        expect(Array.isArray(body)).toBe(true);
    });

    // ── Stub endpoints ──
    it("GET /auth/callback returns 410 Gone", async () => {
        const req = new Request("https://dailypain.hugh79757.workers.dev/auth/callback");
        const res = await worker.fetch(req, env);
        expect(res.status).toBe(410);
    });

    it("GET /deauth returns 410 Gone", async () => {
        const req = new Request("https://dailypain.hugh79757.workers.dev/deauth");
        const res = await worker.fetch(req, env);
        expect(res.status).toBe(410);
    });

    it("POST /data-deletion returns 410 Gone", async () => {
        const req = new Request("https://dailypain.hugh79757.workers.dev/data-deletion", { method: "POST" });
        const res = await worker.fetch(req, env);
        expect(res.status).toBe(410);
    });

    // ── Root ──
    it("GET / returns HTML dashboard", async () => {
        const req = new Request("https://dailypain.hugh79757.workers.dev/");
        const res = await worker.fetch(req, env);
        expect(res.status).toBe(200);
        expect(res.headers.get("Content-Type")).toContain("text/html");
        const text = await res.text();
        expect(text).toContain("DailyPain");
        expect(text).toContain("<!DOCTYPE html>");
    });
});
