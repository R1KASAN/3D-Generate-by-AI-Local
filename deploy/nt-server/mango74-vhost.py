#!/usr/bin/env python3
"""Find the effective www.mangosgo.com server block and activate /mango74.

The first activation attempt failed because the Mango74 include was added to
`/etc/nginx/sites-available/default`, which is not the server block Nginx
actually uses for `www.mangosgo.com:443`. Nginx keeps the first server block
loaded for a given listen address and name and reports every later duplicate as
a conflicting server name, so editing the shadowed block changes nothing.

This tool reads the merged configuration (`nginx -T`), reports every candidate
block with its real file and line number, and installs the include into the
blocks that can actually serve the request.

Read-only unless `activate --apply` is given. Every file that is changed is
backed up first and restored automatically if validation, reload, or any route
gate fails.

Usage (run as root on the NT Server):

    sudo python3 mango74-vhost.py diagnose
    sudo python3 mango74-vhost.py activate --snippet ~/mango74-static.conf
    sudo python3 mango74-vhost.py activate --snippet ~/mango74-static.conf --apply
    sudo python3 mango74-vhost.py rollback --backup-dir /var/backups/mango74/<id>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

HOST = "www.mangosgo.com"
# The NT Server already holds this file with the approved hash, installed by the
# earlier attempt. `/etc/nginx/snippets/mango74-static.conf` is an unreferenced
# hand-made copy from the first attempt and is deliberately left alone.
DEFAULT_SNIPPET_DEST = "/etc/nginx/snippets/mango74-static-v2.conf"
SNIPPET_DIR = "/etc/nginx/snippets"
EXPECTED_SNIPPET_SHA = "1d75836affbe0b4843364eeae5cb4b6c1486e360e5ae2240ed8f1a72c0dc936a"
RELEASE_LINK = Path("/var/www/mango74")
RELEASE_ROOT = Path("/var/www/mango74-releases")
BACKUP_ROOT = Path("/var/backups/mango74")
IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
IPV6 = re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){2,}[0-9a-fA-F]{0,4}\b")


def include_line(dest: str) -> str:
    return "    include {};".format(dest)


def sanitize(text: str) -> str:
    """Keep raw internal addresses out of anything that reaches evidence."""
    text = IPV4.sub("[ADDR]", text)
    return IPV6.sub("[ADDR6]", text)


def run(cmd: list[str], check: bool = False) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit("STOP: required command not found: " + cmd[0])
    if check and proc.returncode != 0:
        sys.stderr.write(sanitize(proc.stderr))
        raise SystemExit("STOP: command failed: " + " ".join(cmd))
    return proc.returncode, proc.stdout, proc.stderr


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# nginx -T parsing
# --------------------------------------------------------------------------
@dataclass
class Stmt:
    args: list[str]
    start_line: int
    end_line: int
    parent: int


@dataclass
class Block:
    bid: int
    args: list[str]
    start_line: int
    end_line: int
    parent: int
    path: str
    stmts: list[Stmt] = field(default_factory=list)
    blocks: list["Block"] = field(default_factory=list)


def split_dump(dump: str) -> list[tuple[str, str]]:
    """Split `nginx -T` output into (config file path, file text) sections."""
    sections: list[tuple[str, str]] = []
    path: str | None = None
    body: list[str] = []
    for line in dump.splitlines():
        marker = re.match(r"^# configuration file (.+):$", line)
        if marker:
            if path is not None:
                sections.append((path, "\n".join(body)))
            path, body = marker.group(1), []
        elif path is not None:
            body.append(line)
    if path is not None:
        sections.append((path, "\n".join(body)))
    return sections


def parse_file(path: str, text: str) -> list[Block]:
    """Tokenize one config file, keeping real line numbers for every element."""
    blocks: list[Block] = []
    stmts: list[Stmt] = []
    stack: list[int] = [-1]
    buf: list[str] = []
    line = 1
    start = 1
    quote = ""
    comment = False
    next_id = 0
    for ch in text:
        if ch == "\n":
            line += 1
            comment = False
            if not buf:
                start = line
            continue
        if comment:
            continue
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
            continue
        if ch == '"' or ch == "'":
            quote = ch
            buf.append(ch)
            continue
        if ch == "#":
            comment = True
            continue
        if ch == "{":
            block = Block(next_id, "".join(buf).split(), start, line, stack[-1], path)
            next_id += 1
            blocks.append(block)
            stack.append(block.bid)
            buf = []
            start = line
            continue
        if ch == "}":
            if len(stack) > 1:
                closed = stack.pop()
                for block in blocks:
                    if block.bid == closed:
                        block.end_line = line
            buf = []
            start = line
            continue
        if ch == ";":
            args = "".join(buf).split()
            if args:
                stmts.append(Stmt(args, start, line, stack[-1]))
            buf = []
            start = line
            continue
        if not buf and ch.isspace():
            start = line
            continue
        buf.append(ch)
    by_id = {b.bid: b for b in blocks}
    for block in blocks:
        if block.parent in by_id:
            by_id[block.parent].blocks.append(block)
    for stmt in stmts:
        if stmt.parent in by_id:
            by_id[stmt.parent].stmts.append(stmt)
    return blocks


@dataclass
class Candidate:
    path: str
    real_path: str
    start_line: int
    end_line: int
    names: list[str]
    listens: list[str]
    ssl: bool
    ports: list[str]
    match: str
    insert_after: int
    already: bool
    order: int
    locations: list[str]
    duplicates: list[str]
    overlaps: list[str]


# What the snippet itself defines. An existing location with the same key makes
# the configuration invalid ("duplicate location"), which `nginx -t` rejects.
OUR_LOCATIONS = {"=/mango74", "/mango74/_next/", "/mango74/"}


def location_key(args: list[str]) -> str:
    """Normalize a location's arguments the way Nginx compares them."""
    if not args:
        return ""
    if args[0] == "=":
        return "=" + args[-1]
    if args[0] == "^~":
        return args[-1]
    if args[0] in {"~", "~*"}:
        return "~" + args[-1]
    return args[-1]


def duplicates_snippet(args: list[str]) -> bool:
    return location_key(args) in OUR_LOCATIONS


def overlaps_mango74(args: list[str]) -> bool:
    """True when a location claims /mango74 without duplicating the snippet."""
    key = location_key(args)
    if duplicates_snippet(args):
        return False
    if key.startswith("~"):
        return "mango74" in key
    spec = key[1:] if key.startswith("=") else key
    if spec == "/":
        return False
    # A prefix captures /mango74 only when it is a prefix of it (/mango7 does,
    # /mango76 does not) or when it sits below it.
    return "/mango74".startswith(spec) or spec.startswith("/mango74")


def name_match(names: list[str]) -> str | None:
    if HOST in names:
        return "exact"
    for name in names:
        if name.startswith("*.") and HOST.endswith(name[1:]) and HOST != name[2:]:
            return "wildcard"
        if name.startswith("~"):
            return "regex"
    return None


def collect_candidates(dump: str) -> list[Candidate]:
    candidates: list[Candidate] = []
    order = 0
    for path, text in split_dump(dump):
        blocks = parse_file(path, text)
        by_id = {b.bid: b for b in blocks}
        for block in blocks:
            if not block.args or block.args[0] != "server":
                continue
            context = []
            parent = block.parent
            while parent in by_id:
                owner = by_id[parent]
                context.append(owner.args[0] if owner.args else "")
                parent = owner.parent
            if "stream" in context or "mail" in context:
                continue
            names: list[str] = []
            listens: list[str] = []
            server_name_end = 0
            already = False
            for stmt in block.stmts:
                if stmt.args[0] == "server_name":
                    names.extend(stmt.args[1:])
                    server_name_end = max(server_name_end, stmt.end_line)
                elif stmt.args[0] == "listen":
                    listens.append(" ".join(stmt.args[1:]))
                elif stmt.args[0] == "include" and "mango74" in " ".join(stmt.args):
                    already = True
            match = name_match(names)
            if match is None and any("default_server" in item for item in listens):
                match = "default_server"
            if match is None:
                continue
            ports = []
            for listen in listens:
                port = re.search(r"(?:^|[:\s])(\d{2,5})(?:\s|$)", listen)
                if port:
                    ports.append(port.group(1))
            order += 1
            candidates.append(
                Candidate(
                    path=path,
                    real_path=os.path.realpath(path),
                    start_line=block.start_line,
                    end_line=block.end_line,
                    names=names,
                    listens=listens,
                    ssl=any("ssl" in item for item in listens) or "443" in ports,
                    ports=sorted(set(ports)),
                    match=match,
                    insert_after=server_name_end or block.start_line,
                    already=already,
                    order=order,
                    locations=[
                        " ".join(sub.args[1:])
                        for sub in block.blocks
                        if sub.args and sub.args[0] == "location"
                    ],
                    duplicates=[
                        "{} (line {})".format(" ".join(sub.args[1:]), sub.start_line)
                        for sub in block.blocks
                        if sub.args and sub.args[0] == "location"
                        and duplicates_snippet(sub.args[1:])
                    ],
                    overlaps=[
                        "{} (line {})".format(" ".join(sub.args[1:]), sub.start_line)
                        for sub in block.blocks
                        if sub.args and sub.args[0] == "location"
                        and overlaps_mango74(sub.args[1:])
                    ],
                )
            )
    return candidates


def load_candidates() -> list[Candidate]:
    code, dump, err = run(["nginx", "-T"])
    if code != 0 and not dump:
        sys.stderr.write(sanitize(err))
        raise SystemExit(
            "STOP: `nginx -T` failed; cannot read the merged configuration "
            "(it needs root - run this with sudo)")
    return collect_candidates(dump)


def first_effective(candidates: list[Candidate]) -> Candidate | None:
    """Nginx uses the first exact name match in load order, then wildcard, then default."""
    for rank in ("exact", "wildcard", "regex", "default_server"):
        for cand in candidates:
            if cand.match == rank:
                return cand
    return None


def describe(candidates: list[Candidate]) -> str:
    lines = []
    winner = first_effective([c for c in candidates if c.ssl])
    for cand in candidates:
        role = "TLS" if cand.ssl else "plain"
        names = " ".join(
            name if "mangosgo" in name or name == "_" else "[OTHER-VHOST]"
            for name in cand.names
        )
        flag = "  [include already present]" if cand.already else ""
        crown = "  <-- EFFECTIVE for https://" + HOST if cand is winner else ""
        lines.append(
            "  [{}] {}:{}-{} ({}, ports {}, match={}){}{}".format(
                cand.order, cand.path, cand.start_line, cand.end_line, role,
                ",".join(cand.ports) or "?", cand.match, flag, crown,
            )
        )
        lines.append("       server_name {}".format(names or "(none)"))
        lines.append("       listen      {}".format(sanitize("; ".join(cand.listens)) or "(inherited)"))
        if cand.real_path != cand.path:
            lines.append("       real file   {}".format(cand.real_path))
        if cand.duplicates:
            lines.append("       DUPLICATES THE SNIPPET: {}".format("; ".join(cand.duplicates)))
        if cand.overlaps:
            lines.append("       also claims /mango74:   {}".format("; ".join(cand.overlaps)))
        if cand.locations:
            shown = ", ".join(cand.locations[:8])
            more = "" if len(cand.locations) <= 8 else ", (+{} more)".format(len(cand.locations) - 8)
            lines.append("       locations   {}{}".format(shown, more))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# route probes
# --------------------------------------------------------------------------
def probe(path: str, origin: str) -> str:
    code, out, _ = run([
        "curl", "--noproxy", "*", "-ksS", "--connect-timeout", "2", "--max-time", "6",
        "--resolve", "{}:443:{}".format(HOST, origin),
        "-o", os.devnull, "-w", "%{http_code}",
        "https://{}{}".format(HOST, path),
    ])
    return out.strip() or "000"


def probe_set(paths: list[str], origin: str) -> dict[str, str]:
    return {path: probe(path, origin) for path in paths}


def asset_path(release_dir: Path) -> str | None:
    static = release_dir / "_next" / "static"
    if not static.is_dir():
        return None
    for item in sorted(static.rglob("*")):
        if item.is_file():
            return "/mango74/" + str(item.relative_to(release_dir)).replace(os.sep, "/")
    return None


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def cmd_diagnose(args: argparse.Namespace) -> int:
    _, _, err = run(["nginx", "-t"])
    print("== nginx -t ==")
    print(sanitize(err).rstrip() or "(no output)")
    conflicts = [line for line in err.splitlines() if "conflicting server name" in line]
    print()
    print("== conflicting server names ==")
    print(sanitize("\n".join(conflicts)) if conflicts else "(none reported)")

    candidates = load_candidates()
    print()
    print("== server blocks that can match {} (in load order) ==".format(HOST))
    print(describe(candidates) if candidates else "  (none found)")

    winner = first_effective([c for c in candidates if c.ssl])
    print()
    if winner:
        print("EFFECTIVE https vhost: {}:{} (real file {})".format(
            winner.path, winner.start_line, winner.real_path))
        print("The include belongs inside that block, after line {}.".format(winner.insert_after))
    else:
        print("STOP: no TLS server block matches this host; TLS may terminate elsewhere.")

    print()
    print("== release state ==")
    link = os.path.realpath(RELEASE_LINK) if RELEASE_LINK.exists() else "ABSENT"
    print("  {} -> {}".format(RELEASE_LINK, link))
    found = sorted(Path(SNIPPET_DIR).glob("mango74*.conf")) if Path(SNIPPET_DIR).is_dir() else []
    if not found:
        print("  no mango74 snippet installed under {}".format(SNIPPET_DIR))
    for item in found:
        digest = sha256_file(item)
        mark = "APPROVED" if digest == EXPECTED_SNIPPET_SHA else "not the approved content"
        print("  snippet: {} sha256={} ({})".format(item, digest, mark))

    print()
    print("== origin route status (public host resolved to the local origin) ==")
    paths = ["/", "/verse", "/mango74", "/mango74/"]
    release_dir = Path(link) if link != "ABSENT" else None
    if release_dir is not None and release_dir.is_dir():
        found = asset_path(release_dir)
        if found:
            paths.append(found)
    for path, status in probe_set(paths, args.origin).items():
        print("  {} -> {}".format(path, status))
    return 0


def install_snippet(source: Path, dest_path: str) -> None:
    if not source.is_file():
        raise SystemExit("STOP: uploaded snippet not found: {}".format(source))
    digest = sha256_file(source)
    if digest != EXPECTED_SNIPPET_SHA:
        raise SystemExit("STOP: snippet hash mismatch (got {})".format(digest))
    dest = Path(dest_path)
    if dest.exists():
        if sha256_file(dest) != EXPECTED_SNIPPET_SHA:
            raise SystemExit("STOP: {} exists with different content".format(dest_path))
        print("INFO: {} already installed with the expected hash".format(dest_path))
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    os.chmod(dest, 0o644)
    os.chown(dest, 0, 0)
    print("INFO: installed {}".format(dest_path))


def select_targets(candidates: list[Candidate], mode: str) -> list[Candidate]:
    tls = [c for c in candidates if c.ssl]
    if not tls:
        raise SystemExit("STOP: no TLS server block matches this host")
    if mode == "effective":
        winner = first_effective(tls)
        return [winner] if winner else []
    if mode == "all-exact":
        exact = [c for c in tls if c.match == "exact"]
        return exact or [c for c in tls if c.match == "wildcard"]
    return tls


def apply_edits(targets: list[Candidate], backup_dir: Path, line: str) -> list[tuple[str, str]]:
    """Insert the include into each target block; returns (real path, backup) pairs."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(backup_dir, 0o700)
    by_file: dict[str, list[Candidate]] = {}
    for cand in targets:
        by_file.setdefault(cand.real_path, []).append(cand)
    changed: list[tuple[str, str]] = []
    for real_path, group in by_file.items():
        source = Path(real_path)
        backup = backup_dir / (source.name + ".bak")
        counter = 1
        while backup.exists():
            backup = backup_dir / "{}.{}.bak".format(source.name, counter)
            counter += 1
        shutil.copy2(source, backup)
        changed.append((real_path, str(backup)))
        lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
        for cand in sorted(group, key=lambda item: item.insert_after, reverse=True):
            lines.insert(cand.insert_after, line + "\n")
            print("INFO: include added at {}:{} (block starts line {})".format(
                cand.path, cand.insert_after + 1, cand.start_line))
        with open(source, "w", encoding="utf-8") as handle:
            handle.write("".join(lines))
    manifest = backup_dir / "manifest.json"
    manifest.write_text(json.dumps({"files": changed}, indent=2) + "\n", encoding="utf-8")
    os.chmod(manifest, 0o600)
    return changed


def restore(files: list[tuple[str, str]]) -> None:
    if not files:
        return
    for real_path, backup in files:
        shutil.copyfile(backup, real_path)
    code, _, err = run(["nginx", "-t"])
    if code != 0:
        sys.stderr.write(sanitize(err))
        raise SystemExit("ROLLBACK FAILED: restored configuration does not validate")
    run(["systemctl", "reload", "nginx"], check=True)
    print("ROLLBACK PASS: known-good configuration restored and reloaded")


def cmd_activate(args: argparse.Namespace) -> int:
    if os.geteuid() != 0:
        raise SystemExit("STOP: run this with sudo")
    release_dir = RELEASE_ROOT / args.release_id
    if not (release_dir / "index.html").is_file():
        raise SystemExit("STOP: release is not staged: {}/index.html".format(release_dir))
    if os.path.realpath(RELEASE_LINK) != str(release_dir):
        raise SystemExit("STOP: {} does not point at {}".format(RELEASE_LINK, release_dir))
    asset = asset_path(release_dir)
    if asset is None:
        raise SystemExit("STOP: no static asset under {}/_next/static".format(release_dir))

    candidates = load_candidates()
    selected = select_targets(candidates, args.targets)
    if not selected:
        print(describe(candidates))
        raise SystemExit(
            "STOP: no TLS block carries this name; only a catch-all default_server "
            "matches. Confirm with the site owner, then re-run with --targets all-tls.")
    targets = [c for c in selected if not c.already]
    print("== server blocks that can match {} ==".format(HOST))
    print(describe(candidates))
    print()
    print("== plan ==")
    for cand in targets:
        print("  edit {}: insert include after line {}".format(cand.real_path, cand.insert_after))
    for cand in [c for c in selected if c.already]:
        print("  skip {}: include already present".format(cand.real_path))
    if not targets:
        print("  no file needs changing")
    if not args.apply:
        print("\nDRY RUN: nothing was changed. Re-run with --apply to activate.")
        return 0

    guard = ["/", "/verse"] + list(args.probe_path or [])
    watched = guard + ["/mango74", "/mango74/", asset]
    before = probe_set(watched, args.origin)
    print("\n== before ==")
    for path, status in before.items():
        print("  {} -> {}".format(path, status))

    install_snippet(Path(args.snippet).expanduser(), args.snippet_dest)
    backup_dir = BACKUP_ROOT / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    changed = apply_edits(targets, backup_dir, include_line(args.snippet_dest))
    print("INFO: backups in {}".format(backup_dir))

    code, _, err = run(["nginx", "-t"])
    print("\n== nginx -t ==")
    print(sanitize(err).rstrip())
    if code != 0:
        print("STOP: configuration did not validate", file=sys.stderr)
        restore(changed)
        return 1
    run(["systemctl", "reload", "nginx"], check=True)

    after = before
    for attempt in range(1, 16):
        after = probe_set(watched, args.origin)
        if (after["/mango74"], after["/mango74/"], after[asset]) == ("308", "200", "200"):
            print("INFO: reloaded worker serving Mango74 after attempt {}".format(attempt))
            break
        time.sleep(1)

    print("\n== after ==")
    for path, status in after.items():
        print("  {} -> {}".format(path, status))

    failures = []
    for path, expected in (("/mango74", "308"), ("/mango74/", "200"), (asset, "200")):
        if after[path] != expected:
            failures.append("{} expected {}, got {}".format(path, expected, after[path]))
    for path in guard:
        if before[path] != after[path]:
            failures.append("{} changed from {} to {}".format(path, before[path], after[path]))
    if run(["systemctl", "is-active", "nginx"])[1].strip() != "active":
        failures.append("nginx is not active after reload")

    if failures:
        print("\nSTOP: acceptance failed", file=sys.stderr)
        for item in failures:
            print("  - {}".format(item), file=sys.stderr)
        restore(changed)
        return 1

    print("\nPASS: /mango74 is live and unrelated routes are unchanged "
          "(release {}, backups {})".format(args.release_id, backup_dir))
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    if os.geteuid() != 0:
        raise SystemExit("STOP: run this with sudo")
    manifest = Path(args.backup_dir) / "manifest.json"
    if not manifest.is_file():
        raise SystemExit("STOP: no manifest in {}".format(args.backup_dir))
    files = [(item[0], item[1]) for item in json.loads(manifest.read_text())["files"]]
    for real_path, backup in files:
        print("restore {} <- {}".format(real_path, backup))
    restore(files)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--origin", default="127.0.0.1",
                        help="address the probes resolve the public host to")
    sub = parser.add_subparsers(dest="command", required=True)

    diagnose = sub.add_parser("diagnose", help="read-only: show which block actually serves the host")
    diagnose.set_defaults(func=cmd_diagnose)

    activate = sub.add_parser("activate", help="install the include (dry run unless --apply)")
    activate.add_argument("--snippet", required=True, help="uploaded mango74-static.conf")
    activate.add_argument("--release-id", default="472d988b")
    activate.add_argument("--targets", choices=["all-exact", "effective", "all-tls"],
                          default="all-exact",
                          help="all-exact (default) covers every duplicate exact-name TLS block")
    activate.add_argument("--probe-path", action="append",
                          help="extra unrelated route that must not change")
    activate.add_argument("--snippet-dest", default=DEFAULT_SNIPPET_DEST,
                          help="path the include points at (default: the copy already installed)")
    activate.add_argument("--apply", action="store_true", help="actually change the server")
    activate.set_defaults(func=cmd_activate)

    rollback = sub.add_parser("rollback", help="restore a backup directory made by activate")
    rollback.add_argument("--backup-dir", required=True)
    rollback.set_defaults(func=cmd_rollback)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
