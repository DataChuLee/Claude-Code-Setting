"""Check the visible save result against a local demo. Never posts to GitHub."""

import argparse
import json


def main() -> int:
    from playwright.sync_api import expect, sync_playwright

    parser = argparse.ArgumentParser(description="Check memo persistence after reload")
    parser.add_argument("--url", required=True)
    parser.add_argument("--expect", choices=("persistent", "lost"), required=True)
    args = parser.parse_args()
    note = "QA reproduction note"
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 1000})
            page.set_default_timeout(5000)
            page.goto(args.url)
            page.get_by_role("button", name="테스트 데이터 초기화", exact=True).click()
            page.get_by_label("메모 내용", exact=True).fill(note)
            page.get_by_role("button", name="메모 저장", exact=True).click()
            expect(page.get_by_role("status")).to_have_text("메모가 저장되었습니다.")
            page.reload()
            observed = page.locator("#saved-note").inner_text() == note
            print(
                json.dumps(
                    {"expected": args.expect, "persistent_after_reload": observed}
                )
            )
            return int(observed != (args.expect == "persistent"))
        finally:
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
