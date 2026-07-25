# screensaver.matrix

## Matrix screensavers for Kodi 21 (Omega)
This addon adds the Matrix screensavers to Kodi Entertainment Center.

## Plugin Features
- JSON-based video playlist fetching and playback
- 1080p 60fps
- Filtering of videos
- Online or offline mode (5.85GB)
  - Download location by scene or all at once
  - Full offline mode to prevent all network calls, using only local videos and JSON
  - Validation to prevent unnecessary re-downloading of cached videos
- Display Power Management Signaling (DPMS) configurable
  - When the display is supposed to go to sleep, pause/stop the Matrix video and turn the display off or put it into standby via HDMI CEC

## Project layout
Each extension point in `addon.xml` maps to one module under
`resources/lib/entrypoints/`. Kodi only puts the running script's own directory
on `sys.path`, so every entry point adds `resources/lib` to it before importing
anything; from there on all imports are absolute (`from core.addon import ...`).

```
addon.xml
resources/
  settings.xml
  language/                the .po files
  playlist/playlist.json   scene names and video URLs
  skins/default/           the window definitions
  lib/
    entrypoints/
      screensaver_entry.py   xbmc.ui.screensaver -- hands over to the script
      script_entry.py        xbmc.python.script  -- plays or downloads
      service_entry.py       xbmc.service        -- clears the lock at startup
    core/
      addon.py               settings, dialogs and translations
      logger.py              prefixed logging
      assets.py              the 17 scenes and their settings and labels
    gui/
      skin.py                window definitions and control ids
      screensaver.py         the window that plays the videos
      preview.py             the loading screen shown before playback starts
      transparent.py         placeholder shown while a video is already running
    playback/
      playlist.py            builds the shuffled rotation from playlist.json
      player.py              the xbmc.Player subclass used for playback
    download/
      picker.py              the "Download Videos" selection dialog
      downloader.py          parallel downloads with progress and cancel support
```
