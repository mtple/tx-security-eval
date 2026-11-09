#!/usr/bin/env python3
"""Which stored rows would get a different prompt from today's renderer? Prints the rerun commands.

Usage: python3 scripts/changed_prompts.py [results/current.jsonl] [--manifest OUT.json]

For every row whose view is alone, context or flows (tools prompts carry no briefing), the user prompt is
rendered exactly as harness/run_models.py renders it and compared with the row's stored prompt, and the system
prompt is compared with harness/prompts.json. Rows that differ are grouped by (model, prompt, task, variant,
view) and printed as run_models.py commands with --sample-ids, one output file per model, so the rerun is the
manifest and nothing else. Needs no RPC and calls no model.
"""
import sys, json, pathlib, collections, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
import run_models  # noqa: E402  (user_prompt, PROMPTS)

def main(argv):
    src = ROOT / "results" / "current.jsonl"; manifest = None
    args = list(argv)
    if "--manifest" in args:
        i = args.index("--manifest"); manifest = pathlib.Path(args[i + 1]); del args[i:i + 2]
    if args: src = pathlib.Path(args[0])
    rows = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
    changed, same, skipped = [], 0, 0
    cache = {}
    for r in rows:
        if r["view"] not in ("alone", "context", "flows"): skipped += 1; continue
        pn = r.get("prompt_name") or "default"
        k = (r["task"], r["variant"], r["view"])
        if k not in cache: cache[k] = run_models.user_prompt(*k)
        if cache[k] == r["prompt"] and run_models.PROMPTS[pn] == r["system"]: same += 1
        else: changed.append(r)
    print(f"{len(rows)} rows: {same} unchanged, {len(changed)} changed, {skipped} tools rows not compared")
    groups = collections.defaultdict(list)
    for r in changed: groups[(r["model"], r.get("prompt_name") or "default", r["task"], r["variant"], r["view"])].append(int(r.get("sample", 0)))
    items = sorted({(t, v, vw) for (_, _, t, v, vw) in groups})
    print("changed (task, variant, view):", items)
    if manifest:
        manifest.write_text(json.dumps([{"model": m, "prompt": p, "task": t, "variant": v, "view": vw, "samples": sorted(s)}
                                        for (m, p, t, v, vw), s in sorted(groups.items())], indent=1))
        print("manifest ->", manifest)
    print("\n# rerun commands (one call per changed row; cc: routes need `env -u CLAUDECODE`):")
    by_model = collections.defaultdict(list)
    for (m, p, t, v, vw), s in sorted(groups.items()): by_model[m].append((p, t, v, vw, sorted(s)))
    for m, specs in by_model.items():
        slug = re.sub(r"[^a-z0-9]+", "-", m.lower()).strip("-")
        pre = "env -u CLAUDECODE " if m.startswith("cc:") else ""
        for p, t, v, vw, s in specs:
            print(f"{pre}python3 harness/run_models.py --models {m} --tasks {t} --variants {v} --views {vw} "
                  f"--sample-ids {','.join(map(str, s))}" + (f" --prompt {p}" if p != "default" else "") +
                  f" --out results/run-final-{slug}-{t}-{v}-{vw}{'-' + p if p != 'default' else ''}.jsonl")
    print(f"\n{len(changed)} calls in all")

if __name__ == "__main__":
    main(sys.argv[1:])
