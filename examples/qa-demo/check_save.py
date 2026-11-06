"""Check the visible save result against a local demo. Never posts to GitHub."""

import argparse
import json
import traceback
from pathlib import Path


def main() -> int:
    from playwright.sync_api import expect, sync_playwright

    parser = argparse.ArgumentParser(description="Check memo persistence after reload")
    parser.add_argument("--url", required=True)
    parser.add_argument("--expect", choices=("persistent", "lost"), required=True)
    parser.add_argument(
        "--output", type=Path, help="Save screenshot, trace and result JSON"
    )
    args = parser.parse_args()
    if args.output:
        args.output.mkdir(parents=True, exist_ok=False)
    note = "QA reproduction note"
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 1000})
        page = context.new_page()
        result = {"url": args.url, "expected": args.expect, "passed": False}
        if args.output:
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            page.set_default_timeout(5000)
            page.goto(args.url)
            page.get_by_role("button", name="테스트 데이터 초기화", exact=True).click()
            page.get_by_label("메모 내용", exact=True).fill(note)
            page.get_by_role("button", name="메모 저장", exact=True).click()
            expect(page.get_by_role("status")).to_have_text("메모가 저장되었습니다.")
            page.reload()
            observed = page.locator("#saved-note").inner_text() == note
            result["persistent_after_reload"] = observed
            expect(page.locator("#saved-note")).to_have_text(
                note if args.expect == "persistent" else "아직 저장된 메모가 없습니다."
            )
            expect(page.get_by_label("메모 내용", exact=True)).to_have_value(
                note if args.expect == "persistent" else ""
            )
            result["passed"] = True
        except Exception as error:
            result["error"] = str(error)
            traceback.print_exc()
        finally:
            if args.output:
                (args.output / "result.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                try:
                    page.screenshot(
                        path=str(args.output / "screen.png"), full_page=True
                    )
                finally:
                    context.tracing.stop(path=str(args.output / "trace.zip"))
            context.close()
            browser.close()
        print(json.dumps(result, ensure_ascii=False))
        return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
