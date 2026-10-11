# Aadya Water Buddy — Modular Python Project

A macOS desktop water reminder with an animated companion, water-intake dashboard, and a local Ollama-powered chatbot.

## Project layout

- `main.py` — starts the Qt application.
- `config.py` — shared paths and asset constants.
- `core/buddy.py` — desktop companion, animation, reminders, menu-bar actions, and app coordination.
- `core/settings.py` — settings dialog.
- `water/dashboard.py` — water dashboard, chart, and water-entry CRUD.
- `chatbot/chat_window.py` — chatbot UI and background Ollama request worker.
- `assets/` — empty asset skeleton; add your own character images here.

## Add your own character images and animations

The repository intentionally does **not** include the original character images. The `assets/` folder contains only the folder skeleton, so each person can use their own images.

### 1. Add the main character images

Put two transparent PNG images directly in `assets/` and name them exactly:

- `aadya_happy.png` — the happy/normal character image.
- `aadya_sad.png` — the sad character image shown when you choose “Later”.

You can use your own character, cartoon, mascot, or water-drop illustration. Keep the background transparent for the cleanest desktop-sticker appearance.

### 2. Add animation frames

Copy individual PNG frames into these folders:

```text
assets/
├── aadya_happy.png
├── aadya_sad.png
├── dance_happy/
│   ├── frame_01.png
│   ├── frame_02.png
│   └── ...
├── happy_walk/
│   ├── frame_01.png
│   ├── frame_02.png
│   └── ...
└── sad_walk/
    ├── frame_01.png
    ├── frame_02.png
    └── ...
```

- `dance_happy/` — frames for the happy entrance/dance.
- `happy_walk/` — frames for walking away after you confirm drinking water.
- `sad_walk/` — frames for walking away after you choose “Later”.
- Use **individual image files**, not a combined sprite sheet. PNG is recommended; transparent backgrounds are recommended.
- Keep each animation's frames the same dimensions and name them in sequence, for example `frame_01.png`, `frame_02.png`, `frame_03.png`, and so on. The app loads frames in filename order.
- If you only have one image, you can start with that image copied into a frame folder, but the animation will look static. For smooth movement, add multiple sequential frames.

### 3. Asset files are intentionally ignored by Git

The repository's `.gitignore` excludes image files under `assets/` so personal photos and character artwork are not accidentally committed. Your local files still work when you run the app. The `.gitkeep` files preserve the empty folder structure in Git.

If you intentionally want to contribute reusable, licensed sample artwork to a fork, review and edit the asset ignore rules first, and make sure you have permission to share the images.

## Keep your existing data

The application stores persistent data at:

`~/Library/Application Support/AadyaWaterBuddy/water_log.json`

Settings are stored at:

`~/Library/Application Support/AadyaWaterBuddy/settings.json`

These are local runtime files and should not be committed to Git.

## Install and run (macOS)

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Ollama should be running locally with the model used by the app:

```bash
ollama pull qwen3:8b
ollama serve
```

If Ollama is already running, do not start a second server process.

## Notes

Run the app from the project root with `python main.py` so imports resolve consistently. Add your own assets before running if you want the animated character to display correctly.
