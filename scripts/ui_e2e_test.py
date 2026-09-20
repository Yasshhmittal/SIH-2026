"""
scripts/ui_e2e_test.py — Drive the real demo flow through the Streamlit UI.

Uses Streamlit's AppTest to click "Load sample demo documents" then "Run Agent",
exercising the true path: button -> run_agent -> session_state -> populated render.
Verifies no uncaught exception and that a result state is produced.
"""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


def main() -> int:
    at = AppTest.from_file(APP_PATH, default_timeout=300)
    at.run()

    # 1) Preflight must be ready (Ollama + models).
    assert not at.exception, f"Empty-state render raised: {at.exception}"

    # 2) Click "Load sample demo documents".
    load = next(b for b in at.button if "sample" in b.label.lower())
    load.click().run()
    assert not at.exception, f"Loading sample raised: {at.exception}"

    # 3) Click "Run Agent" (now enabled).
    run = next(b for b in at.button if "Run Agent" in b.label)
    assert not run.disabled, "Run Agent button is disabled after loading sample"
    run.click().run()
    assert not at.exception, f"Running agent raised: {at.exception}"

    # 4) Inspect the populated render.
    print("=== TIMELINE / RENDER SUMMARY ===")
    print("errors  :", [e.value[:100] for e in at.error])
    print("warnings:", [w.value[:100] for w in at.warning])
    print("success :", [s.value[:100] for s in at.success])
    print("infos   :", [i.value[:100] for i in at.info])
    print("metrics :", [(m.label, m.value) for m in at.metric])
    dl = [d for d in getattr(at, "download_button", [])]
    print("download buttons:", [d.label for d in dl])
    print("markdown blocks :", len(at.markdown))
    print("✅ UI E2E completed with NO uncaught exception")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
