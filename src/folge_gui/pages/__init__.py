"""Page builders for folge_gui.

Each module exposes a single ``build()`` function that renders one page's
content (called from within an ``@ui.page`` handler in ``app.py``). Keeping
route registration in ``app.py`` and content in these modules keeps each
page's accessibility concerns (headings, landmarks, live regions) colocated
with the content that needs them.
"""
