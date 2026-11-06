"use strict";

// The broken route intentionally confirms a save without persisting it.
const broken = true;
const storageKey = `fieldnotes-qa-demo:${broken ? "broken" : "fixed"}`;
document.body.dataset.mode = broken ? "broken" : "fixed";
document.body.innerHTML = `
  <a class="skip-link" href="#content">메모 작성으로 이동</a>
  <div class="page">
    <header class="masthead">
      <a class="brand" href="/" aria-label="Fieldnotes 홈"><span class="brand-mark" aria-hidden="true">f.</span>Fieldnotes<span class="brand-sub">a little QA notebook</span></a>
      <nav class="modes" aria-label="테스트 버전">
        <a href="/broken/" ${broken ? 'aria-current="page"' : ""}>오류 재현</a>
        <a href="/fixed/" ${!broken ? 'aria-current="page"' : ""}>수정 버전</a>
      </nav>
    </header>
    <main id="content">
      <section class="intro" aria-labelledby="title">
        <div><p class="eyebrow">EXPERIMENT 01 <span>기록과 저장</span></p>
          <h1 id="title">작은 기록을,<br><em>확실하게.</em></h1>
          <p class="lead">메모를 적고 저장한 다음, 새로고침해 보세요.<br>남아 있는 기록으로 저장 결과를 확인합니다.</p>
        </div>
        <aside class="version-note">
          <span class="mode-badge">${broken ? "오류 재현 버전" : "수정 버전"}</span>
          <p>${broken ? "저장 안내가 나와도 새로고침 후 메모가 사라지는 상황을 재현합니다." : "저장한 메모가 새로고침 후에도 유지되는지 확인할 수 있습니다."}</p>
          <span class="test-only">테스트 전용 · 실제 개인정보 입력 금지</span>
        </aside>
      </section>
      <div class="workspace">
        <section class="editor" aria-labelledby="editor-title">
          <div class="section-label"><span>01 / WRITE</span><span id="count">0 / 300</span></div>
          <h2 id="editor-title">오늘의 한 줄</h2>
          <label class="input-label" for="memo">메모 내용</label>
          <textarea id="memo" maxlength="300" placeholder="오늘 기억하고 싶은 일을 적어보세요." aria-describedby="input-help"></textarea>
          <p class="input-help" id="input-help">최대 300자. 저장 버튼을 눌러야 기록됩니다.</p>
          <div class="actions"><button class="primary" id="save" type="button">메모 저장 <span aria-hidden="true">↗</span></button><button class="secondary" id="reload" type="button">새로고침</button></div>
          <p id="status" class="status" role="status" aria-live="polite"></p>
        </section>
        <section class="saved" aria-labelledby="saved-title">
          <div class="section-label"><span>02 / KEEP</span><span aria-hidden="true">✳</span></div>
          <h2 id="saved-title">저장된 메모</h2>
          <div class="saved-note-wrap"><p id="saved-note" class="saved-note"></p></div>
          <p id="saved-time" class="saved-time"></p>
          <div class="saved-footer"><span>FIELDNOTES / LOCAL EDITION</span><span aria-hidden="true">01</span></div>
        </section>
      </div>
      <section class="walkthrough" aria-label="확인 순서">
        <p>직접 확인해 보세요</p><ol><li><span>1</span> 메모 입력</li><li><span>2</span> 저장하기</li><li><span>3</span> 새로고침 후 비교</li></ol>
        <button id="reset" type="button">테스트 데이터 초기화</button>
      </section>
    </main>
    <footer class="footer"><span>Small notes. Clear evidence.</span><span>로컬 QA 실험 화면</span></footer>
  </div>`;

const memo = document.querySelector("#memo");
const savedNote = document.querySelector("#saved-note");
const savedTime = document.querySelector("#saved-time");
const status = document.querySelector("#status");
const counter = document.querySelector("#count");

function announce(message, error = false) {
  status.textContent = message;
  status.dataset.error = String(error);
}

function display(record) {
  savedNote.textContent = record ? record.text : "아직 저장된 메모가 없습니다.";
  savedNote.classList.toggle("empty", !record);
  savedTime.textContent = record ? "이 브라우저에 작성한 테스트 메모" : "첫 기록을 기다리고 있어요.";
  memo.value = record ? record.text : "";
  counter.textContent = `${memo.value.length} / 300`;
}

try {
  const raw = localStorage.getItem(storageKey);
  const record = raw ? JSON.parse(raw) : null;
  display(record && typeof record.text === "string" && record.text.length <= 300 ? record : null);
} catch {
  display(null);
  announce("저장된 메모를 읽지 못했습니다. 초기화 후 다시 확인해 주세요.", true);
}

memo.addEventListener("input", () => {
  counter.textContent = `${memo.value.length} / 300`;
  announce("");
});

document.querySelector("#save").addEventListener("click", () => {
  const text = memo.value.trim();
  if (!text) {
    announce("메모 내용을 입력해 주세요.", true);
    memo.focus();
    return;
  }
  try {
    if (!broken) localStorage.setItem(storageKey, JSON.stringify({ text }));
    display({ text });
    announce("메모가 저장되었습니다.");
  } catch {
    announce("메모를 저장하지 못했습니다. 브라우저의 저장 설정을 확인해 주세요.", true);
  }
});

document.querySelector("#reload").addEventListener("click", () => location.reload());
document.querySelector("#reset").addEventListener("click", () => {
  try {
    localStorage.removeItem(storageKey);
    display(null);
    announce("테스트용 메모를 초기화했습니다.");
  } catch {
    announce("초기화하지 못했습니다. 브라우저의 저장 설정을 확인해 주세요.", true);
  }
});
