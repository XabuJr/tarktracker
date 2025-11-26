# TarkTracker Data Repository

This repository contains data files for the TarkTracker desktop application.

## Purpose

TarkTracker is an Electron desktop application for tracking Escape from Tarkov hideout upgrades and quest items. This repository hosts the JSON data files that the application downloads on startup to ensure users always have the latest data.

## Data Files

- **hideout.json** - Hideout module requirements (28 modules with item/currency/trader requirements)
- **quests.json** - Quest item requirements (manually curated list)
- **item_images.json** - Item image mappings for display in the application

## Usage

These files are automatically downloaded by the TarkTracker application on launch. Users do not need to manually interact with this repository.

## Updates

Data files are updated periodically to reflect:
- New hideout modules or level changes
- Quest requirement updates
- New items and image mappings

The application checks for updates each time it launches and downloads fresh data if available.

## Version

Current data version: 2025-11-26
