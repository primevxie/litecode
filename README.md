litecode (smol vscode-ish, powered by pyside6)

how 2 run

1) make venv n feed it deps:
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2) boot it:
```
python app.py
```

what u get

- dark cozy theme, minimal chrome
- sidebar explorer (double‑click to open stuff)
- tabbed editor w/ line numbers + lil glow on current line
- open/save/save as + open folder
- movable tabs, dirty dot when unsaved, optional autosave (File → Auto Save)
- drag & drop files/folders right onto the window
- status bar whispers ur cursor coords
- shortcuts: Ctrl+N / Ctrl+O / Ctrl+S / Ctrl+Shift+S / Ctrl+W / Ctrl+Tab / Ctrl+Shift+Tab

tweak me

- colors live in `resources/theme.qss`
- code is tiny n friendly, great base for adding syntax highlight, find/replace, etc


