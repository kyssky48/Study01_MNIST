// 생성: 2026-09-20 19:14 (KST)
// 그림판에 그린 그림을 MNIST와 같은 형식(28x28)으로 바꾼다.
// 파이썬 쪽 draw_app.py의 전처리() 함수와 같은 절차를 따른다.
//   1. 글씨가 있는 영역의 경계 상자를 잘라낸다
//   2. 비율을 유지한 채 긴 변을 20픽셀로 줄인다
//   3. 28x28 검은 바탕 가운데에 붙인다
//   4. 무게중심이 (13.5, 13.5)에 오도록 평행 이동한다
// MNIST 자체가 이 방식으로 만들어진 데이터라, 맞춰 주어야 학습한 성능이 나온다.

// 캔버스에서 밝기값만 뽑아낸다 (검은 바탕에 흰 글씨이므로 빨강 채널을 쓴다)
export function 캔버스에서_밝기뽑기(캔버스) {
  const 맥락 = 캔버스.getContext("2d", { willReadFrequently: true });
  const 화상 = 맥락.getImageData(0, 0, 캔버스.width, 캔버스.height);
  const 밝기 = new Float32Array(캔버스.width * 캔버스.height);
  for (let i = 0; i < 밝기.length; i++) {
    밝기[i] = 화상.data[i * 4];
  }
  return { 밝기, 너비: 캔버스.width, 높이: 캔버스.height };
}

// 영역 평균으로 축소한다. 줄이는 방향이므로 원본 화소를 골고루 반영한다.
function 축소(원본, 원너비, 원높이, 새너비, 새높이) {
  const 결과 = new Float32Array(새너비 * 새높이);
  const 가로비 = 원너비 / 새너비;
  const 세로비 = 원높이 / 새높이;

  for (let y = 0; y < 새높이; y++) {
    const 위 = Math.floor(y * 세로비);
    const 아래 = Math.max(위 + 1, Math.ceil((y + 1) * 세로비));

    for (let x = 0; x < 새너비; x++) {
      const 왼쪽 = Math.floor(x * 가로비);
      const 오른쪽 = Math.max(왼쪽 + 1, Math.ceil((x + 1) * 가로비));

      let 합 = 0;
      let 개수 = 0;
      for (let 행 = 위; 행 < 아래 && 행 < 원높이; 행++) {
        for (let 열 = 왼쪽; 열 < 오른쪽 && 열 < 원너비; 열++) {
          합 += 원본[행 * 원너비 + 열];
          개수++;
        }
      }
      결과[y * 새너비 + x] = 개수 > 0 ? 합 / 개수 : 0;
    }
  }
  return 결과;
}

// 무게중심이 가운데 오도록 평행 이동한다 (넘파이 roll과 같이 가장자리를 감싼다)
function 무게중심_맞추기(화소) {
  let 총합 = 0;
  let 가중_x = 0;
  let 가중_y = 0;

  for (let y = 0; y < 28; y++) {
    for (let x = 0; x < 28; x++) {
      const 값 = 화소[y * 28 + x];
      총합 += 값;
      가중_x += x * 값;
      가중_y += y * 값;
    }
  }
  if (총합 <= 0) return 화소;

  const 이동_x = Math.round(13.5 - 가중_x / 총합);
  const 이동_y = Math.round(13.5 - 가중_y / 총합);
  if (이동_x === 0 && 이동_y === 0) return 화소;

  const 결과 = new Float32Array(784);
  for (let y = 0; y < 28; y++) {
    const 새y = ((y + 이동_y) % 28 + 28) % 28;
    for (let x = 0; x < 28; x++) {
      const 새x = ((x + 이동_x) % 28 + 28) % 28;
      결과[새y * 28 + 새x] = 화소[y * 28 + x];
    }
  }
  return 결과;
}

// 밝기 배열을 받아 28x28 밝기값(0~255)을 돌려준다.
// 아무것도 그리지 않았으면 null을 돌려준다.
export function 전처리(밝기, 너비, 높이) {
  // 1. 경계 상자 찾기
  let 위 = 높이;
  let 아래 = -1;
  let 왼쪽 = 너비;
  let 오른쪽 = -1;

  for (let y = 0; y < 높이; y++) {
    for (let x = 0; x < 너비; x++) {
      if (밝기[y * 너비 + x] > 0) {
        if (y < 위) 위 = y;
        if (y > 아래) 아래 = y;
        if (x < 왼쪽) 왼쪽 = x;
        if (x > 오른쪽) 오른쪽 = x;
      }
    }
  }
  if (아래 < 0) return null;   // 빈 그림

  // 2. 잘라내기
  const 자른너비 = 오른쪽 - 왼쪽 + 1;
  const 자른높이 = 아래 - 위 + 1;
  const 자른것 = new Float32Array(자른너비 * 자른높이);
  for (let y = 0; y < 자른높이; y++) {
    for (let x = 0; x < 자른너비; x++) {
      자른것[y * 자른너비 + x] = 밝기[(위 + y) * 너비 + (왼쪽 + x)];
    }
  }

  // 3. 긴 변을 20픽셀로 맞춰 축소
  let 새너비;
  let 새높이;
  if (자른너비 > 자른높이) {
    새너비 = 20;
    새높이 = Math.max(1, Math.round(자른높이 * 20 / 자른너비));
  } else {
    새높이 = 20;
    새너비 = Math.max(1, Math.round(자른너비 * 20 / 자른높이));
  }
  const 줄인것 = 축소(자른것, 자른너비, 자른높이, 새너비, 새높이);

  // 4. 28x28 가운데에 붙이기
  const 바탕 = new Float32Array(784);
  const 왼쪽여백 = Math.floor((28 - 새너비) / 2);
  const 위여백 = Math.floor((28 - 새높이) / 2);
  for (let y = 0; y < 새높이; y++) {
    for (let x = 0; x < 새너비; x++) {
      바탕[(위여백 + y) * 28 + (왼쪽여백 + x)] = 줄인것[y * 새너비 + x];
    }
  }

  // 5. 무게중심 정렬
  return 무게중심_맞추기(바탕);
}
