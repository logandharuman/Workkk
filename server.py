#!/usr/bin/env python3
"""
DevMem SSH Tool - Backend Server v2
Python 3.13+ stdlib only. No pip.
Uses Windows built-in ssh.exe (OpenSSH) for SSH transport.
"""

import http.server
import json
import subprocess
import csv
import io
import os
import time

# ── SSH runtime config ────────────────────────────────────────────────────────
ssh_cfg = {"host": "", "username": "", "password": ""}

WIN_SSH = r"C:\Windows\System32\OpenSSH\ssh.exe"
SSH_EXE = WIN_SSH if os.path.exists(WIN_SSH) else "ssh"


# ── Core SSH runner ───────────────────────────────────────────────────────────
def _run(cmd: str) -> dict:
    h, u, p = ssh_cfg["host"], ssh_cfg["username"], ssh_cfg["password"]
    if not h or not u:
        return {"out": "", "err": "SSH not configured.", "rc": -1}

    args = [SSH_EXE,
            "-o", "StrictHostKeyChecking=no",
            "-o", "BatchMode=no",
            "-o", "ConnectTimeout=10",
            "-o", "LogLevel=ERROR",
            f"{u}@{h}", cmd]

    env = os.environ.copy()
    if os.name == "nt":
        hp = os.path.join(os.environ.get("TEMP", r"C:\Temp"), "_dm_askpass.bat")
        with open(hp, "w") as f:
            f.write(f"@echo {p}\n")
        env["SSH_ASKPASS"] = hp
    else:
        hp = "/tmp/_dm_askpass.sh"
        with open(hp, "w") as f:
            f.write(f"#!/bin/sh\necho '{p}'\n")
        os.chmod(hp, 0o700)
        env["SSH_ASKPASS"] = hp

    env["SSH_ASKPASS_REQUIRE"] = "force"
    env["DISPLAY"] = "dummy"

    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=15, env=env)
        return {"out": r.stdout.strip(), "err": r.stderr.strip(), "rc": r.returncode}
    except subprocess.TimeoutExpired:
        return {"out": "", "err": "Timed out.", "rc": -1}
    except FileNotFoundError:
        return {"out": "", "err": f"ssh.exe not found: {SSH_EXE}", "rc": -1}
    except Exception as e:
        return {"out": "", "err": str(e), "rc": -1}


def _fmt(v: str) -> str:
    v = v.strip()
    return v if v.lower().startswith("0x") else "0x" + v


def do_read(addr: str) -> dict:
    r = _run(f"devmem {_fmt(addr)}")
    if r["rc"] == 0 and r["out"]:
        return {"ok": True, "value": r["out"]}
    return {"ok": False, "value": "ERROR", "error": r["err"] or r["out"]}


def do_write(addr: str, val: str) -> dict:
    r = _run(f"devmem {_fmt(addr)} 32 {_fmt(val)}")
    if r["rc"] == 0:
        return {"ok": True}
    return {"ok": False, "error": r["err"] or r["out"]}


def batch_read(rows):
    out = []
    for row in rows:
        addr = (row.get("address") or row.get("Address") or row.get("ADDR") or "").strip()
        if not addr:
            out.append({**row, "read_value": "NO_ADDR", "status": "error"}); continue
        res = do_read(addr)
        out.append({**row,
                    "read_value": res["value"] if res["ok"] else f"ERROR:{res.get('error','')}",
                    "status": "ok" if res["ok"] else "error"})
        time.sleep(0.04)
    return out


def batch_write(rows):
    out = []
    for row in rows:
        addr = (row.get("address") or row.get("Address") or "").strip()
        val  = (row.get("data")    or row.get("Data")    or row.get("value") or "").strip()
        if not addr or not val:
            out.append({**row, "write_status": "MISSING", "status": "error"}); continue
        res = do_write(addr, val)
        out.append({**row,
                    "write_status": "OK" if res["ok"] else f"ERROR:{res.get('error','')}",
                    "status": "ok" if res["ok"] else "error"})
        time.sleep(0.04)
    return out


def batch_custom(rows):
    out = []
    for row in rows:
        addr = (row.get("address") or row.get("Address") or "").strip()
        val  = (row.get("data")    or row.get("Data")    or "").strip()
        rw   = (row.get("rw") or row.get("RW") or row.get("r/w") or "r").strip().lower()

        if not addr:
            out.append({**row, "result": "NO_ADDR", "status": "error"}); continue

        if rw == "w":
            if not val:
                out.append({**row, "result": "NO_DATA", "status": "error"}); continue
            res = do_write(addr, val)
            out.append({**row,
                        "result": "WRITE_OK" if res["ok"] else f"ERROR:{res.get('error','')}",
                        "status": "ok" if res["ok"] else "error"})
        else:
            res = do_read(addr)
            out.append({**row,
                        "result": res["value"] if res["ok"] else f"ERROR:{res.get('error','')}",
                        "status": "ok" if res["ok"] else "error"})
        time.sleep(0.04)
    return out


# ── HTTP handler ──────────────────────────────────────────────────────────────
class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, *a): pass

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _csv_dl(self, rows):
        if not rows:
            self._json({"ok": False, "error": "No rows"}); return
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
        body = buf.getvalue().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/csv")
        self.send_header("Content-Disposition", 'attachment; filename="devmem_results.csv"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers(); self.wfile.write(body)

    def _serve(self, fpath, ct):
        try:
            with open(fpath, "rb") as f: d = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(d)))
            self.end_headers(); self.wfile.write(d)
        except FileNotFoundError:
            self.send_response(404); self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        for h, v in [("Access-Control-Allow-Origin","*"),
                     ("Access-Control-Allow-Methods","GET,POST,OPTIONS"),
                     ("Access-Control-Allow-Headers","Content-Type")]:
            self.send_header(h, v)
        self.end_headers()

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._serve("index.html", "text/html")
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            p = json.loads(raw) if raw else {}
        except Exception:
            self._json({"ok": False, "error": "Bad JSON"}, 400); return

        ep = self.path

        if ep == "/api/connect":
            ssh_cfg["host"]     = p.get("host", "")
            ssh_cfg["username"] = p.get("username", "")
            ssh_cfg["password"] = p.get("password", "")
            r = _run("echo __OK__")
            ok = "__OK__" in r["out"]
            self._json({"ok": ok, "message": f"Connected to {ssh_cfg['host']}" if ok else (r["err"] or r["out"] or "Auth failed")})

        elif ep == "/api/read_one":
            addr = p.get("address", "")
            self._json(do_read(addr) if addr else {"ok": False, "error": "No address"})

        elif ep == "/api/write_one":
            addr, val = p.get("address",""), p.get("value","")
            self._json(do_write(addr, val) if addr and val else {"ok": False, "error": "address+value required"})

        elif ep == "/api/run":
            mode = p.get("mode", "read")
            rows = p.get("rows", [])
            if not rows:
                self._json({"ok": False, "error": "No rows"}); return
            fn = {"read": batch_read, "write": batch_write, "custom": batch_custom}.get(mode)
            if not fn:
                self._json({"ok": False, "error": "Unknown mode"}); return
            self._json({"ok": True, "results": fn(rows)})

        elif ep == "/api/export":
            self._csv_dl(p.get("rows", []))

        else:
            self._json({"ok": False, "error": "Unknown endpoint"}, 404)


if __name__ == "__main__":
    PORT = 8765
    srv = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"\n  DevMem Register Tool v2")
    print(f"  http://127.0.0.1:{PORT}")
    print(f"  SSH: {SSH_EXE}")
    print(f"  Ctrl+C to stop\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
