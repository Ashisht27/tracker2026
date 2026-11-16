"""Merge helper for the WhatsApp Outreach Queue <-> GitHub sync.

Claude runs this during a sync. It does the file work only; Claude reads and
writes the page's shared storage and republishes the page.

  python sync_merge.py --db <dir of status/*.json dumps> [--page <page.html>]

Statuses: for each lead, the newer change (by `at`) wins. status.json is
rewritten with the merged result, and db_writes.json lists the storage writes
needed so the page matches.

Leads: with --page, compares leads.json with the page's LEADS list and writes
leads_line.js (the new `const LEADS = ...;` line) when the repo has leads the
page doesn't, or when lead details changed.
"""
import argparse, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
STATES = {"sent", "replied", "pdf_sent", "not_interested", "stop", "skip"}


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def read_db(db_dir):
    out = {}
    if not db_dir or not os.path.isdir(db_dir):
        return out
    for name in os.listdir(db_dir):
        if not name.endswith(".json"):
            continue
        doc = load(os.path.join(db_dir, name), {})
        data = doc.get("data", doc) if isinstance(doc, dict) else {}
        out[name[:-5]] = {"data": {k: data.get(k, "") for k in ("state", "at", "sentAt")},
                          "version": doc.get("version") if isinstance(doc, dict) else None}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", help="folder holding status/<id>.json dumps")
    ap.add_argument("--page", help="saved page HTML, to compare leads")
    a = ap.parse_args()

    leads = load(os.path.join(HERE, "leads.json"), [])
    ids = {l["id"] for l in leads}
    repo = load(os.path.join(HERE, "status.json"), {})
    db = read_db(a.db)

    merged, writes = {}, []
    for lid in sorted(set(repo) | set(db)):
        r, d = repo.get(lid), db.get(lid, {}).get("data")
        if r and r.get("state") not in STATES:
            print(f"! ignoring repo status for {lid}: unknown state {r.get('state')!r}")
            r = None
        if lid not in ids:
            print(f"! status for unknown lead {lid}")
        win = max([x for x in (r, d) if x], key=lambda x: x.get("at", ""), default=None)
        if not win:
            continue
        merged[lid] = win
        if win is not d:
            w = {"op": "set", "collection": "status", "doc_id": lid, "data": win}
            if lid in db and db[lid]["version"]:
                w["if_version"] = db[lid]["version"]
            writes.append(w)

    with open(os.path.join(HERE, "status.json"), "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, sort_keys=True)
    with open(os.path.join(HERE, "db_writes.json"), "w", encoding="utf-8") as f:
        json.dump(writes, f, indent=2)
    print(f"statuses: {len(merged)} total, {len(writes)} to write to the page")

    if a.page:
        with open(a.page, encoding="utf-8") as f:
            m = re.search(r"^const LEADS = (.*);\s*$", f.read(), re.M)
        page = json.loads(m.group(1)) if m else []
        pids = {l["id"]: l for l in page}
        new = [l for l in leads if l["id"] not in pids]
        changed = [l for l in leads if l["id"] in pids and l != pids[l["id"]]]
        missing_pdf = [l["id"] for l in new if not l.get("bl")]
        print(f"leads: {len(new)} new, {len(changed)} changed, "
              f"{len(set(pids) - ids)} only on the page (kept)")
        if missing_pdf:
            print(f"  {len(missing_pdf)} new leads have no PDF uploaded yet")
        if new or changed:
            keep = [l for l in page if l["id"] not in ids]
            line = "const LEADS = " + json.dumps(leads + keep, ensure_ascii=False) + ";"
            with open(os.path.join(HERE, "leads_line.js"), "w", encoding="utf-8") as f:
                f.write(line)
            print("  wrote leads_line.js for republishing")


if __name__ == "__main__":
    main()
