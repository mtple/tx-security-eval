#!/usr/bin/env python3
"""Regenerate a Safe's executed-transaction history file (tasks/bybit-history.json shape)
from the Safe transaction service.

Usage: python3 scripts/fetch_safe_history.py <safe-address> <out.json>
e.g.   python3 scripts/fetch_safe_history.py 0x1Db92e2EeBC8E0c075a02BeA49a2935BcD2dFCF4 tasks/bybit-history.json

Fetches multisig-transactions?limit=100&executed=true (following next-page links and
redirects), keeps executed+successful entries ordered by nonce. Only the fetch date in
_note differs between runs.
"""
import json, sys, datetime, urllib.request

HOST = "safe-transaction-mainnet.safe.global"

def get(url):
    req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "tx-security-eval-fetch/1"})
    with urllib.request.urlopen(req, timeout=60) as r:  # urllib follows redirects
        return json.loads(r.read())

def main():
    if len(sys.argv) != 3: sys.exit(__doc__)
    safe, out = sys.argv[1], sys.argv[2]
    url = f"https://{HOST}/api/v1/safes/{safe}/multisig-transactions/?limit=100&executed=true"
    results = []
    while url:
        page = get(url); results += page["results"]; url = page.get("next")
    entries = []
    for t in results:
        if t.get("isExecuted") is False: continue
        entries.append({
            "nonce": t["nonce"],
            "date": t["executionDate"].split(".")[0].rstrip("Z") + "Z",
            "block": t["blockNumber"],
            "tx_hash": t["transactionHash"],
            "to": t["to"],
            "value_eth": int(t["value"]) / 1e18,
            "operation": t["operation"],
            "data_selector": (t.get("data") or "")[:10] or None,
            "executor": t["executor"],
            "confirmations": len(t.get("confirmations") or []),
            "threshold": t["confirmationsRequired"],
        })
    entries.sort(key=lambda e: e["nonce"])
    today = datetime.date.today().isoformat()
    doc = {"_note": f"Executed transactions of the Bybit cold-wallet Safe {safe}, from the Safe transaction service ({HOST}), fetched {today}. The renderer only uses entries whose block precedes the request being rendered.",
           "entries": entries}
    with open(out, "w") as f:
        json.dump(doc, f, indent=1)  # no trailing newline, matching the committed file
    print(f"{len(entries)} entries -> {out}")

if __name__ == "__main__":
    main()
