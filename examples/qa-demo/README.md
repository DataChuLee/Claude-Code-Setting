# 메모 저장 오류 재현 데모

이슈 → 수정 → PR 흐름을 확인하는 로컬 HTML/CSS/JavaScript 데모다. npm 설치와 외부 폰트는 필요 없다. 실제 개인정보는 입력하지 않는다.

프로젝트 루트에서 서버를 실행한다.

```powershell
python -m http.server 4174 --bind 127.0.0.1 --directory examples/qa-demo
```

http://127.0.0.1:4174/ 에서 메모 입력 → 저장 → 새로고침 순서로 확인한다. 저장 안내와 실제 데이터 유지 여부를 따로 검사한다.

이 기준 커밋에서는 모든 경로가 오류 재현 모드로 고정되어 있으며 정상 유지 검사는 종료 코드 1을 반환한다. 이후 수정 커밋에서 기본 화면과 수정 버전을 정상 동작으로 전환한다.

## 브라우저 검사

선택적으로 Playwright와 Chromium을 설치한 환경에서 검사한다. 기존 기본 CI에 브라우저 설치를 요구하지 않는다.

```powershell
python -m pip install playwright
python -m playwright install chromium
python examples/qa-demo/check_save.py --url http://127.0.0.1:4174/ --expect persistent
```

데이터가 유지되지 않으면 종료 코드 1, 유지되면 0이다. `--expect lost`는 오류가 재현되는 비교용 화면을 확인할 때만 사용한다. 이는 저장 기능이 정상이라는 뜻이 아니다.

실제 서버·계정·DB 저장을 검증하지 않는 localStorage 데모다. 테스트 데이터 초기화는 현재 버전의 데모 키만 지운다. 상세 촬영 증거는 연결된 GitHub 이슈와 PR에 첨부한다.
