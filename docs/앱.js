// 생성: 2026-09-20 19:14 (KST)
// 웹 버전의 진입점. 그림판·전처리·모델을 이어 붙인다.

import { 숫자인식모델 } from "./모델.js";
import { 그림판 } from "./그림판.js";
import { 캔버스에서_밝기뽑기, 전처리 } from "./전처리.js";

const 캔버스 = document.getElementById("그림판");
const 미리보기 = document.getElementById("미리보기");
const 결과숫자 = document.getElementById("결과숫자");
const 결과설명 = document.getElementById("결과설명");
const 확률목록 = document.getElementById("확률목록");
const 상태 = document.getElementById("상태");
const 인식단추 = document.getElementById("인식단추");
const 지우기단추 = document.getElementById("지우기단추");

let 모델 = null;
const 판 = new 그림판(캔버스);

// 28x28 전처리 결과를 작은 캔버스에 그려 보여 준다
function 미리보기_그리기(화소) {
  const 맥락 = 미리보기.getContext("2d");
  const 화상 = 맥락.createImageData(28, 28);
  for (let i = 0; i < 784; i++) {
    const 값 = 화소 ? Math.max(0, Math.min(255, Math.round(화소[i]))) : 0;
    화상.data[i * 4] = 값;
    화상.data[i * 4 + 1] = 값;
    화상.data[i * 4 + 2] = 값;
    화상.data[i * 4 + 3] = 255;
  }
  맥락.putImageData(화상, 0, 0);
}

function 결과_비우기(안내) {
  결과숫자.textContent = "?";
  결과설명.textContent = 안내;
  확률목록.innerHTML = "";
  미리보기_그리기(null);
}

function 인식() {
  if (!모델) return;

  const { 밝기, 너비, 높이 } = 캔버스에서_밝기뽑기(캔버스);
  const 화소 = 전처리(밝기, 너비, 높이);
  if (!화소) {
    결과_비우기("숫자를 그려 보세요");
    return;
  }
  미리보기_그리기(화소);

  const 시작시각 = performance.now();
  const 로그확률 = 모델.화소로_추론(화소);
  const 걸린시간 = performance.now() - 시작시각;

  const 확률 = Array.from(로그확률, (값) => Math.exp(값));
  const 순서 = 확률.map((값, 숫자) => ({ 숫자, 값 }))
                   .sort((가, 나) => 나.값 - 가.값);

  결과숫자.textContent = String(순서[0].숫자);
  결과설명.textContent = `확신도 ${(순서[0].값 * 100).toFixed(1)}% · ${걸린시간.toFixed(0)}ms`;

  확률목록.innerHTML = "";
  for (const { 숫자, 값 } of 순서.slice(0, 3)) {
    const 줄 = document.createElement("div");
    줄.className = "확률줄";
    줄.innerHTML = `
      <span class="확률숫자">${숫자}</span>
      <span class="확률막대"><i style="width:${(값 * 100).toFixed(1)}%"></i></span>
      <span class="확률값">${(값 * 100).toFixed(1)}%</span>`;
    확률목록.appendChild(줄);
  }
}

판.그림그린뒤 = 인식;          // 획을 마치면 바로 인식
인식단추.addEventListener("click", 인식);
지우기단추.addEventListener("click", () => {
  판.지우기();
  결과_비우기("숫자를 그려 보세요");
});

// 가중치는 4.6MB라 받는 동안 안내를 띄운다
(async () => {
  try {
    상태.textContent = "모델을 불러오는 중입니다 (약 4.6MB)…";
    모델 = await 숫자인식모델.불러오기();
    상태.textContent = "";
    상태.classList.add("숨김");
    인식단추.disabled = false;
    지우기단추.disabled = false;
    결과_비우기("숫자를 그려 보세요");
  } catch (오류) {
    상태.textContent = `모델을 불러오지 못했습니다: ${오류.message}`;
    상태.classList.add("오류");
  }
})();
