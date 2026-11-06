# PR 브라우저 QA

상태: 승인됨 (2026-11-06, 대화에서 메모 데모의 PR 자동 검사 진행 승인)

## 목적과 완료 조건

- PR 생성·코드 push·재오픈·Ready 전환 시 GitHub Actions에서 메모 저장을 검사한다.
- 입력 → 저장 안내 확인 → 새로고침 후 저장된 메모와 입력란의 내용이 유지되어야 통과한다.
- 메모가 사라지거나 서버·브라우저 실행에 실패하면 QA 검사가 실패한다.
- 성공·실패 화면, 검사 결과 JSON, 브라우저 trace와 실행 로그를 가능한 범위에서 보관한다.
- 제목·본문만 바꿀 때는 실행하지 않는다. Cloudflare·LLM 분석·자동 이슈 생성은 포함하지 않는다.

## 구성과 결과 확인

`.github/workflows/qa.yml`이 별도의 `qa / browser` 검사를 실행한다.
검사는 브라우저 내부 저장소(localStorage) 데모의 기본 화면만 대상으로 한다.
모든 PR에서 실행하며, 코드 변경과 무관한 경로 필터나 API 키는 사용하지 않는다.
PR 병합 결과를 checkout하여 main과 합쳐진 상태를 검사한다.

PR의 검사 목록 → `qa / browser` 실행 → Artifacts의 `qa-evidence-…`를 내려받는다.
화면은 PR 본문에 자동 첨부되지 않는다. 캡처만으로 성공을 판정하지 않고 텍스트 내용도 검사한다.

| 파일 | 확인할 내용 |
|---|---|
| `memo/screen.png` | 검사 종료 시점의 화면 |
| `memo/result.json` | 예상 동작·실제 저장 여부·통과 여부·오류 |
| `memo/trace.zip` | 브라우저 동작 순서와 화면 기록 |
| `browser.log`, `server.log` | 검사 오류와 서버 요청 기록 |

자료는 7일 보관하며, 설치 실패 등 브라우저를 열기 전 실패에는 화면·trace가 없을 수 있다.
실행 중인 오래된 QA는 새 push가 들어오면 취소한다.
읽기 권한만 사용하며, 저장소 설정·필수 병합 검사·Claude 리뷰 설정은 변경하지 않는다.
GitHub 정책상 승인이 필요한 실행은 저장소 권한자가 승인해야 시작된다.

## 로컬 확인

README대로 서버를 실행한 뒤 Playwright와 Chromium이 설치된 환경에서 실행한다.
`--output`에는 아직 없는 폴더를 지정한다. 옵션을 생략하면 기존처럼 결과만 출력한다.

```powershell
python examples/qa-demo/check_save.py --url http://127.0.0.1:4174/ --expect persistent --output tmp/qa-local
python -m playwright show-trace tmp/qa-local/trace.zip
```

검사 자체의 실패 탐지를 확인하려면 `/broken/`에 `--expect persistent`를 적용한다.
이 경우 종료 코드 1과 실패 화면이 나와야 한다. 비교용 `--expect lost` 성공과 구분한다.

## 작업 기록

- [x] 기존 검사에서 `--output` 미지원 실패 확인
- [x] 캡처·trace·JSON 기록과 PR 워크플로 구현
- [x] 정상 화면 통과·오류 화면 실패 및 증거 생성 검증
- [x] 독립 리뷰 — 필수 수정사항 없음

GitHub에서 실행된 최종 결과와 아티팩트는 해당 PR의 `qa / browser` 검사에서 확인한다.
