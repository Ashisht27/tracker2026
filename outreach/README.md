# WhatsApp Outreach Queue: GitHub sync

These files mirror the shared WhatsApp Outreach Queue page on claude.ai.

| File | What it holds |
| --- | --- |
| `leads.json` | Every lead on the page: name, market, city, lead type, phone, prepared message, PDF reference. |
| `status.json` | Each lead's outreach status, keyed by lead id: `state`, `at` (last change), `sentAt`. |
| `sync_merge.py` | Merge helper Claude runs during a sync. |

## How a sync works

Ask Claude to "sync the WhatsApp outreach queue with GitHub". Claude then:

1. Pulls this repo and reads the page's shared status storage.
2. Merges statuses. For each lead the most recent change (by `at`) wins, whether it was made on the page or here.
3. Writes the merged statuses back to the page and commits `status.json` here.
4. Compares `leads.json` with the page. If leads were added or edited here, Claude republishes the page with the new list. Leads that only exist on the page are kept.

## Editing here

- **Add a lead:** append an object to `leads.json` with a unique `id` and the same fields as the others. `m` is `IN` or `US`; `s` is `no_website`, `old_website`, `dead_website` or `fine_website`. Leave `doc` and `bl` empty if there is no PDF yet.
- **Change a status:** set `state` to one of `sent`, `replied`, `pdf_sent`, `not_interested`, `stop`, `skip`, and set `at` to the current time in ISO format (for example `2026-11-16T10:30:00Z`). If `at` is older than the page's change, the page wins.
- **Reset a lead to "To send":** remove it from `status.json` *and* clear it on the page. Removing it here alone won't do it, because the page's entry still exists.

Note: this repo is public, so the lead details here are visible to anyone.
