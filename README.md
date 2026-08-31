# TarkTracker Data Repository

This repository contains data files for the TarkTracker desktop application.

## Purpose

TarkTracker is an Electron desktop application for tracking Escape from Tarkov hideout upgrades and quest items. This repository hosts the JSON data files that the application downloads on startup to ensure users always have the latest data.

## Layout

```
data/
├── hideout.json       # PvP data (kept at top level for app 1.0.0 compatibility)
├── quests.json
├── item_images.json
├── pvp/               # PvP (persistent "regular" game mode)
│   ├── hideout.json
│   ├── quests.json
│   ├── item_images.json
│   └── prices.json
├── pve/               # PvE game mode
│   └── (same four files)
└── pvp-s/             # PvP seasonal ("pvp-season") — hideout has no found-in-raid reqs
    └── (same four files)
```

- **hideout.json** — Hideout module requirements (items, currency, trader loyalty, prerequisite modules, skills, construction time)
- **quests.json** — Every task with item hand-in objectives (item name, quantity, found-in-raid flag, quest giver)
- **item_images.json** — Item name → image URL mappings for display in the application
- **prices.json** — Trader sell prices for every sellable item. Compact form: `traders` is a name array, and each item's `offers` are `[traderIndex, price, priceRUB, currency]` sorted by rouble value. Trader prices only — no flea market.

## Data Source

Data is generated from the [json.tarkov.dev](https://json.tarkov.dev/endpoints) dump API (community-maintained, current with the live game) by `tools/generate_data.py`. To refresh after a game patch:

```
python tools/generate_data.py
git add data && git commit -m "Data refresh" && git push
```

## Updates

The application checks for updates each time it launches and downloads fresh data if available. Data files are updated periodically to reflect:
- Game patches (task rework, hideout requirement changes, etc.)
- New items and image mappings

## Version

Current data version: 2026-08-31 (post-patch 1.1.0.0 / Season 1 "Kord Breach")
