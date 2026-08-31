#!/usr/bin/env python3
"""Generate TarkTracker data files from the json.tarkov.dev dump API.

Produces quests.json, hideout.json, and item_images.json for each game mode
(pvp = "regular", pve = "pve"), matching the schema the TarkTracker app expects.
Top-level data/ holds the PvP files for backward compatibility with app 1.0.0;
data/pvp/ and data/pve/ hold the per-mode files for the tabbed app version.

Usage:  python tools/generate_data.py
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

API = "https://json.tarkov.dev"
MODES = {"pvp": "regular", "pve": "pve", "pvp-s": "pvp-season"}
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CURRENCY_ITEMS = {
    "5449016a4bdc2d6f028b456f": "Rouble",
    "5696686a4bdc2da3298b456a": "Dollar",
    "569668774bdc2da2298b4568": "Euro",
}

# Root handbook categories exposed as price filters, in display order.
# Roots not listed here (task-items, maps — a handful of items) stay
# uncategorized and only appear under "All items".
PRICE_CATEGORIES = [
    ("barter-items", "Barter items"),
    ("keys", "Keys"),
    ("gear", "Gear"),
    ("weapons", "Weapons"),
    ("weapon-parts-mods", "Weapon mods"),
    ("ammo", "Ammo"),
    ("provisions", "Provisions"),
    ("medication", "Meds"),
    ("info-items", "Info items"),
    ("special-equipment", "Special gear"),
]


def fetch(path):
    url = f"{API}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "TarkTracker-data-generator/2.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def construction_time(seconds):
    if not seconds:
        return "Instant"
    if seconds < 3600:
        m = round(seconds / 60)
        return f"{m} minute{'s' if m != 1 else ''}"
    h = round(seconds / 3600)
    return f"{h} hour{'s' if h != 1 else ''}"


def clean_objective_name(desc):
    """Turn a 'Hand over ...' objective description into a display name.

    The found-in-raid wording is dropped because the foundInRaid flag already
    carries it. Returns None when the description is too generic to use.
    """
    n = desc.strip()
    if n.lower().startswith("hand over "):
        n = n[len("hand over "):]
    lowered = n.lower()
    for p in ("the found in raid items: ", "the found in raid item: ",
              "the item: ", "the items: "):
        if lowered.startswith(p):
            n = n[len(p):]
            break
    else:
        for p in ("any found in raid ", "the found in raid ", "one of ",
                  "any ", "the "):
            if lowered.startswith(p):
                n = n[len(p):]
                break
    n = n.strip()
    if not n or n.lower() in ("item", "items"):
        return None
    return n[0].upper() + n[1:]


def build_mode(api_mode, old_images):
    hideout = fetch(f"{api_mode}/hideout")
    hideout_tr = fetch(f"{api_mode}/hideout_en")["data"]
    tasks = fetch(f"{api_mode}/tasks")
    tasks_tr = fetch(f"{api_mode}/tasks_en")["data"]
    items_data = fetch(f"{api_mode}/items")["data"]
    items = items_data["items"]
    handbook = items_data.get("handbookCategories") or {}
    items_tr = fetch(f"{api_mode}/items_en")["data"]
    traders_tr = fetch(f"{api_mode}/traders_en")["data"]

    def item_name(iid):
        rec = items.get(iid)
        if not rec:
            return None
        return items_tr.get(rec["name"], rec.get("normalizedName", iid))

    def item_icon(iid):
        rec = items.get(iid) or {}
        return rec.get("iconLink") or rec.get("gridImageLink")

    stations = hideout["data"]
    station_name = {sid: hideout_tr.get(s["name"], s["name"]) for sid, s in stations.items()}
    version = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    referenced = {}  # item name -> item id

    # ---- hideout.json ----
    modules = []
    for sid, s in sorted(stations.items(), key=lambda kv: station_name[kv[0]]):
        levels = []
        for lvl in sorted(s["levels"], key=lambda l: l["level"]):
            req_items, currencies = [], []
            for ir in lvl.get("itemRequirements", []):
                iid = ir["item"]
                if iid in CURRENCY_ITEMS:
                    currencies.append({"amount": ir["count"], "currency": CURRENCY_ITEMS[iid]})
                    continue
                name = item_name(iid)
                if not name:
                    continue
                referenced[name] = iid
                req_items.append({
                    "quantity": ir["count"],
                    "name": name,
                    "foundInRaid": bool((ir.get("attributes") or {}).get("foundInRaid")),
                })
            traders = [
                {"trader": traders_tr.get(f"{tr['trader']} Nickname", "Unknown"),
                 "loyaltyLevel": tr["value"]}
                for tr in lvl.get("traderRequirements", [])
                if tr.get("requirementType") == "level"
            ]
            mod_reqs = [
                {"module": station_name.get(mr["station"], mr["station"]), "level": mr["level"]}
                for mr in lvl.get("stationLevelRequirements", [])
            ]
            skills = [
                {"skill": hideout_tr.get(sr["skill"], sr["skill"]), "level": sr["level"]}
                for sr in lvl.get("skillRequirements", [])
            ]
            levels.append({
                "level": lvl["level"],
                "requirements": {
                    "items": req_items,
                    "currencies": currencies,
                    "traders": traders,
                    "modules": mod_reqs,
                    "skills": skills,
                },
                "constructionTime": construction_time(lvl.get("constructionTime", 0)),
            })
        modules.append({"name": station_name[sid], "levels": levels})
    hideout_out = {"version": version, "modules": modules}

    # ---- quests.json ----
    quests = []
    for t in tasks["data"]["tasks"].values():
        objectives = [o for o in t["objectives"]
                      if o["type"] == "giveItem" and not o.get("optional")]
        if not objectives:
            continue
        q_items, q_currencies = [], []
        for o in objectives:
            ids = o.get("items", [])
            if not ids:
                continue
            if len(ids) == 1 and ids[0] in CURRENCY_ITEMS:
                q_currencies.append({"amount": o["count"], "currency": CURRENCY_ITEMS[ids[0]]})
                continue
            if len(ids) == 1:
                name = item_name(ids[0])
                if not name:
                    continue
                referenced[name] = ids[0]
            else:
                # any-of objective: derive a display name from its description
                desc = tasks_tr.get(o["description"]) or ""
                name = clean_objective_name(desc) or item_name(ids[0])
                if not name:
                    continue
                referenced.setdefault(name, ids[0])
            q_items.append({
                "name": name,
                "quantity": o["count"],
                "foundInRaid": bool(o.get("foundInRaid")),
            })
        if not q_items and not q_currencies:
            continue
        quests.append({
            "name": tasks_tr.get(t["name"], t["name"]),
            "giver": traders_tr.get(f"{t['trader']} Nickname", "Unknown"),
            "objectives": {
                "items": q_items,
                "currencies": q_currencies,
                "other": [],
                "type": "standard",
            },
        })
    # Repeatable tasks can appear multiple times under the same name (e.g. the
    # BTR Driver's "Battery Change"); progress is tracked by name, so keep one.
    seen_names = set()
    deduped = []
    for q in quests:
        key = (q["giver"], q["name"])
        if key in seen_names:
            continue
        seen_names.add(key)
        deduped.append(q)
    quests = deduped

    quests.sort(key=lambda q: (q["giver"], q["name"]))
    quests_out = {"version": version, "quests": quests}

    # ---- prices.json ----
    # Trader sell prices for every sellable item (not just tracked ones).
    # Each item carries its root handbook category as an index into "cats"
    # ("c"), and "p": 1 marks presets — items sold with their stock
    # plates/attachments installed, which is why they outprice the bare item.
    def hb_root(cid):
        seen = set()
        while cid in handbook and handbook[cid].get("parent") and cid not in seen:
            seen.add(cid)
            cid = handbook[cid]["parent"]
        return cid

    cat_labels = dict(PRICE_CATEGORIES)
    cat_list = [label for _, label in PRICE_CATEGORIES]
    cat_index = {label: i for i, label in enumerate(cat_list)}
    trader_list = []
    trader_index = {}
    price_items = []
    for iid, rec in items.items():
        offers_raw = rec.get("sellToTrader") or []
        if not offers_raw:
            continue
        name = item_name(iid)
        if not name:
            continue
        offers = []
        for o in offers_raw:
            tname = traders_tr.get(f"{o.get('trader')} Nickname")
            if not tname:
                continue
            if tname not in trader_index:
                trader_index[tname] = len(trader_list)
                trader_list.append(tname)
            price = o.get("price") or 0
            price_rub = o.get("priceRUB") or 0
            cur = {"RUB": "RUB", "USD": "USD", "EUR": "EUR"}.get(o.get("currency"))
            if not cur or price_rub <= 0:
                continue
            offers.append([trader_index[tname], int(price), int(price_rub), cur])
        if not offers:
            continue
        offers.sort(key=lambda x: -x[2])
        entry = {"name": name, "icon": item_icon(iid), "offers": offers}
        hbs = rec.get("handbookCategories") or []
        if hbs:
            root = handbook.get(hb_root(hbs[0])) or {}
            label = cat_labels.get(root.get("normalizedName"))
            if label:
                entry["c"] = cat_index[label]
        if "preset" in (rec.get("types") or []):
            entry["p"] = 1
        price_items.append(entry)
    price_items.sort(key=lambda x: x["name"])
    prices_out = {"version": version, "traders": trader_list,
                  "cats": cat_list, "items": price_items}

    # ---- item_images.json ----
    images = {}
    for name, iid in sorted(referenced.items()):
        if name in old_images:
            images[name] = old_images[name]  # keep bundled/wiki images that already work
        else:
            icon = item_icon(iid)
            if icon:
                images[name] = icon
    return hideout_out, quests_out, images, prices_out


def main():
    old_images_path = os.path.join(REPO_ROOT, "data", "item_images.json")
    old_images = {}
    if os.path.exists(old_images_path):
        with open(old_images_path, encoding="utf-8") as f:
            old_images = json.load(f)

    for mode, api_mode in MODES.items():
        print(f"Generating {mode} (API game mode: {api_mode})...")
        hideout_out, quests_out, images, prices_out = build_mode(api_mode, old_images)
        out_dir = os.path.join(REPO_ROOT, "data", mode)
        os.makedirs(out_dir, exist_ok=True)
        targets = [out_dir]
        if mode == "pvp":
            targets.append(os.path.join(REPO_ROOT, "data"))  # backward compat for app 1.0.0
        for d in targets:
            with open(os.path.join(d, "hideout.json"), "w", encoding="utf-8") as f:
                json.dump(hideout_out, f, indent=2, ensure_ascii=False)
            with open(os.path.join(d, "quests.json"), "w", encoding="utf-8") as f:
                json.dump(quests_out, f, indent=2, ensure_ascii=False)
            with open(os.path.join(d, "item_images.json"), "w", encoding="utf-8") as f:
                json.dump(images, f, indent=2, ensure_ascii=False)
            with open(os.path.join(d, "prices.json"), "w", encoding="utf-8") as f:
                json.dump(prices_out, f, separators=(",", ":"), ensure_ascii=False)
        print(f"  {len(hideout_out['modules'])} modules, {len(quests_out['quests'])} quests, "
              f"{len(images)} item images, {len(prices_out['items'])} priced items")
    print("Done.")


if __name__ == "__main__":
    main()
