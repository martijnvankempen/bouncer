#!/usr/bin/env node
// Runs badge/apps/<app> from this repo in the badger.github.io badge simulator,
// reusing the Badge Simulator canvas page from a badger/home clone, without the
// GitHub Copilot app. Open the printed URL in a browser and keep it visible.
//
//   node tools/simulate.mjs [--home ~/src/badger-home] [--app bouncer] [--port 8765]
//
// Scripted control (send the header with every POST):
//   curl -H 'X-Badge-Simulator: 1' -d '{"button":"select","ms":120}' localhost:8765/ctl/press
//   curl -H 'X-Badge-Simulator: 1' -d '{"label":"title"}' localhost:8765/ctl/screenshot
//   curl -H 'X-Badge-Simulator: 1' -d '{"code":"game.score"}' localhost:8765/ctl/exec
//   curl localhost:8765/ctl/status
// Recording (raw frames for tools/capture.py, saved under $TMPDIR/badge-simulator/<app>-<label>/):
//   curl -H 'X-Badge-Simulator: 1' -d '{"label":"fight","fps":30}' localhost:8765/ctl/record-start
//   curl -H 'X-Badge-Simulator: 1' -d '{"id":"<id from record-start>"}' localhost:8765/ctl/record-stop
// Buttons: up, down, left, right, select (physical), pad_up, pad_down, pad_left,
// pad_right, pad_select (touch pad), back, menu, home; combine with "+".
import { createServer } from "node:http";
import { existsSync, mkdirSync, readFileSync, readdirSync, renameSync, statSync, unlinkSync, watch, writeFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { dirname, extname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

const repo = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const { values: opts } = parseArgs({
    options: {
        home: { type: "string", default: join(homedir(), "src", "badger-home") },
        app: { type: "string", default: "bouncer" },
        port: { type: "string", default: "8765" },
    },
});

const webDir = join(resolve(opts.home), ".github", "extensions", "badge-simulator", "web");
if (!existsSync(join(webDir, "BUILD_INFO.json"))) {
    console.error(`No simulator page at ${webDir}; pass --home <badger/home clone>.`);
    process.exit(1);
}
const appDir = join(repo, "badge", "apps", opts.app);
if (!existsSync(join(appDir, "__init__.py"))) {
    console.error(`No app at ${appDir}.`);
    process.exit(1);
}
const { revision } = JSON.parse(readFileSync(join(webDir, "BUILD_INFO.json"), "utf8"));
const runtimeBase = `https://raw.githubusercontent.com/badger/badger.github.io/${revision}/public/simulator/`;
const cacheDir = join(homedir(), ".cache", "badge-simulator", revision);
const shotDir = join(tmpdir(), "badge-simulator");

const mime = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8", ".wasm": "application/wasm",
    ".glb": "model/gltf-binary", ".png": "image/png", ".txt": "text/plain; charset=utf-8",
};
const buttonBits = {
    down: 1, up: 2, select: 4, right: 8, left: 16, home: 32, back: 8192, menu: 16384,
    pad_left: 256, pad_right: 512, pad_select: 1024, pad_up: 2048, pad_down: 4096,
};
const ignored = (name) => name === "__pycache__" || name.endsWith(".pyc") || name.startsWith(".");

const clients = new Set();
const pending = new Map();
const log = [];
const recordings = new Map();
let revisionNo = 0;
let stats = {};

function appFiles(dir, out = []) {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
        if (ignored(entry.name)) continue;
        const full = join(dir, entry.name);
        if (entry.isDirectory()) appFiles(full, out);
        else out.push({ path: relative(appDir, full).split(sep).join("/"), data: readFileSync(full).toString("base64") });
    }
    return out;
}

async function runtimeFile(rel) {
    const file = join(cacheDir, rel);
    if (!file.startsWith(cacheDir + sep)) throw Object.assign(new Error("Bad path"), { status: 400 });
    if (existsSync(file)) return readFileSync(file);
    const response = await fetch(runtimeBase + rel.split("/").map(encodeURIComponent).join("/"));
    if (!response.ok) throw Object.assign(new Error(`${response.status} fetching ${rel}`), { status: response.status });
    const bytes = Buffer.from(await response.arrayBuffer());
    mkdirSync(dirname(file), { recursive: true });
    writeFileSync(`${file}.tmp`, bytes);
    renameSync(`${file}.tmp`, file);
    return bytes;
}

function readRaw(req) {
    return new Promise((ok, fail) => {
        const chunks = [];
        req.on("data", (c) => chunks.push(c));
        req.on("end", () => ok(Buffer.concat(chunks)));
        req.on("error", fail);
    });
}

function readBody(req) {
    return new Promise((ok, fail) => {
        const chunks = [];
        req.on("data", (c) => chunks.push(c));
        req.on("end", () => { try { ok(chunks.length ? JSON.parse(Buffer.concat(chunks).toString("utf8")) : {}); } catch (e) { fail(e); } });
        req.on("error", fail);
    });
}
const json = (res, status, body) => {
    res.writeHead(status, { "Content-Type": mime[".json"], "Cache-Control": "no-store" });
    res.end(JSON.stringify(body));
};
function broadcast(event) {
    for (const client of clients) client.write(`data: ${JSON.stringify(event)}\n\n`);
}
function request(event, timeoutMs) {
    const id = Math.random().toString(36).slice(2, 10);
    return new Promise((done) => {
        const timer = setTimeout(() => { pending.delete(id); done(null); }, timeoutMs);
        pending.set(id, (value) => { clearTimeout(timer); done(value); });
        broadcast({ ...event, id });
    });
}

let execLines = null;
function ingest(lines) {
    for (const line of lines.map(String)) {
        const marker = /^\[sim-exec:([\w-]+):(begin|ok|error)\]$/.exec(line);
        if (marker) {
            const [, id, kind] = marker;
            if (kind === "begin") execLines = [];
            else { pending.get(id)?.({ ok: kind === "ok", output: (execLines ?? []).join("\n") }); pending.delete(id); execLines = null; }
            continue;
        }
        if (execLines) { execLines.push(line); continue; }
        log.push(line);
        console.log(line);
    }
}

async function handle(req, res) {
    const url = new URL(req.url, "http://localhost");
    const path = decodeURIComponent(url.pathname);
    // Loopback only: reject foreign hosts/origins and POSTs without the custom header.
    const host = String(req.headers.host ?? "");
    if (!/^(localhost|127\.0\.0\.1):\d+$/.test(host)) return json(res, 403, { error: "Forbidden" });
    if (req.headers.origin && req.headers.origin !== `http://${host}`) return json(res, 403, { error: "Forbidden" });
    if (req.method === "POST" && req.headers["x-badge-simulator"] !== "1") return json(res, 403, { error: "Forbidden" });

    if (path === "/events") {
        res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-store", Connection: "keep-alive" });
        res.write(": connected\n\n");
        clients.add(res);
        req.on("close", () => clients.delete(res));
        return;
    }
    if (path === "/api/state") return json(res, 200, { apps: [opts.app], app: opts.app });
    if (path === "/api/app") return json(res, 200, { app: opts.app, revision: revisionNo, files: appFiles(appDir) });
    if (path === "/ctl/status") return json(res, 200, { stats, clients: clients.size, log: log.slice(-40) });

    if (req.method === "POST" && path === "/api/record-frame") {
        const data = await readRaw(req);
        const p = url.searchParams;
        recordings.get(p.get("id"))?.frames.push({ t: Number(p.get("t")), w: Number(p.get("w")), h: Number(p.get("h")), data });
        return json(res, 200, { ok: true });
    }
    if (req.method === "POST") {
        const body = await readBody(req);
        if (path === "/api/record-done") { pending.get(body.id)?.(body); pending.delete(body.id); return json(res, 200, { ok: true }); }
        if (path === "/ctl/record-start") {
            const id = Math.random().toString(36).slice(2, 10);
            recordings.set(id, { label: String(body.label ?? id).replace(/[^\w-]+/g, "_"), frames: [] });
            broadcast({ type: "record-start", id, fps: Math.max(1, Math.min(60, Number(body.fps ?? 30))), video: false, scale: 1 });
            return json(res, 200, { id });
        }
        if (path === "/ctl/record-stop") {
            const rec = recordings.get(String(body.id));
            if (!rec) return json(res, 404, { error: "No such recording" });
            const done = new Promise((ok) => {
                const timer = setTimeout(() => { pending.delete(body.id); ok(null); }, 15000);
                pending.set(body.id, (value) => { clearTimeout(timer); ok(value); });
            });
            broadcast({ type: "record-stop", id: body.id });
            await done;
            recordings.delete(String(body.id));
            const dir = join(shotDir, `${opts.app}-${rec.label}`);
            mkdirSync(dir, { recursive: true });
            for (const name of readdirSync(dir)) if (name.endsWith(".rgba")) unlinkSync(join(dir, name));
            rec.frames.sort((a, b) => a.t - b.t);
            rec.frames.forEach((f, i) => writeFileSync(join(dir, `${String(i).padStart(5, "0")}_${f.t.toFixed(1)}_${f.w}x${f.h}.rgba`), f.data));
            return json(res, 200, { dir, frames: rec.frames.length });
        }
        if (path === "/api/log") { ingest(body.lines ?? []); return json(res, 200, { ok: true }); }
        if (path === "/api/stats") { stats = body; return json(res, 200, { ok: true }); }
        if (path === "/api/screenshot") { pending.get(body.id)?.(body.screen); pending.delete(body.id); return json(res, 200, { ok: true }); }
        if (path === "/api/status" || path === "/api/select" || path === "/api/deploy") return json(res, 200, { ok: true });
        if (path === "/ctl/press") {
            const names = String(body.button ?? "").toLowerCase().split("+");
            if (!names.every((n) => buttonBits[n])) return json(res, 400, { error: `Buttons: ${Object.keys(buttonBits).join(", ")}` });
            const bit = names.reduce((mask, n) => mask | buttonBits[n], 0);
            broadcast({ type: "press", bit, ms: Math.max(30, Math.min(10000, Number(body.ms ?? 120))) });
            return json(res, 200, { ok: true });
        }
        if (path === "/ctl/screenshot") {
            const dataUrl = await request({ type: "screenshot" }, 5000);
            if (!dataUrl) return json(res, 504, { error: "No page connected" });
            mkdirSync(shotDir, { recursive: true });
            const file = join(shotDir, `${opts.app}-${String(body.label ?? Date.now()).replace(/[^\w-]+/g, "_")}.png`);
            writeFileSync(file, Buffer.from(String(dataUrl).replace(/^data:image\/png;base64,/, ""), "base64"));
            return json(res, 200, { path: file });
        }
        if (path === "/ctl/exec") {
            const result = await request({ type: "exec", code: String(body.code ?? "") }, 5000);
            return json(res, result ? 200 : 504, result ?? { error: "Timed out" });
        }
        if (path === "/ctl/reload") { revisionNo++; broadcast({ type: "reload", app: opts.app, revision: revisionNo }); return json(res, 200, { ok: true }); }
        return json(res, 404, { error: "Not found" });
    }

    if (path.startsWith("/simulator/")) {
        const rel = path.slice("/simulator/".length);
        const bytes = await runtimeFile(rel);
        res.writeHead(200, { "Content-Type": mime[extname(rel)] ?? "application/octet-stream", "Cache-Control": "max-age=86400" });
        return res.end(bytes);
    }
    const file = resolve(webDir, "." + (path === "/" ? "/index.html" : path));
    if (!file.startsWith(webDir + sep) || !existsSync(file) || !statSync(file).isFile()) return json(res, 404, { error: "Not found" });
    res.writeHead(200, { "Content-Type": mime[extname(file)] ?? "application/octet-stream", "Cache-Control": "no-store" });
    res.end(readFileSync(file));
}

let reloadTimer;
watch(appDir, { recursive: true }, (_type, name) => {
    if (name && String(name).split(/[\\/]/).some(ignored)) return;
    clearTimeout(reloadTimer);
    reloadTimer = setTimeout(() => { revisionNo++; broadcast({ type: "reload", app: opts.app, revision: revisionNo }); }, 300);
});

const server = createServer((req, res) => {
    handle(req, res).catch((error) => {
        if (!res.headersSent) json(res, error.status ?? 500, { error: error.message });
        else res.end();
    });
});
server.listen(Number(opts.port), "127.0.0.1", () => {
    console.log(`Badge simulator for ${opts.app}: http://localhost:${opts.port}/`);
});
