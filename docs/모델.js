// 생성: 2026-09-20 19:14 (KST)
// MNIST 손글씨 숫자 인식 CNN의 순전파를 순수 자바스크립트로 구현한다.
// 구조는 파이썬 쪽 model.py의 숫자인식CNN과 같아야 한다.
//   입력 1x28x28
//   -> 합성곱1(1->32, 3x3) + ReLU      26x26
//   -> 합성곱2(32->64, 3x3) + ReLU     24x24
//   -> 최대풀링(2)                      12x12
//   -> 완전연결1(9216->128) + ReLU
//   -> 완전연결2(128->10)
//   -> 로그소프트맥스
// 추론에서는 드롭아웃이 꺼지므로 구현하지 않는다.

export class 숫자인식모델 {
  constructor(가중치, 정보) {
    this.가중치 = 가중치;   // Float32Array 전체
    this.층 = {};
    for (const 항목 of 정보.층) {
      this.층[항목.이름] = {
        값: 가중치.subarray(항목.시작, 항목.시작 + 항목.개수),
        모양: 항목.모양,
      };
    }
    this.평균 = 정보.평균;
    this.표준편차 = 정보.표준편차;
  }

  // 가중치 파일 두 개를 받아 모델을 만든다
  static async 불러오기(정보주소 = "가중치정보.json", 이진주소 = "가중치.bin") {
    const 정보 = await (await fetch(정보주소)).json();
    const 버퍼 = await (await fetch(이진주소)).arrayBuffer();
    const 가중치 = new Float32Array(버퍼);
    if (가중치.length !== 정보.전체개수) {
      throw new Error(`가중치 개수가 맞지 않습니다: ${가중치.length} != ${정보.전체개수}`);
    }
    return new 숫자인식모델(가중치, 정보);
  }

  // 합성곱: 입력(입력채널 x 크기 x 크기) -> 출력(출력채널 x (크기-2) x (크기-2))
  // 커널은 3x3, 패딩 없음, 스트라이드 1로 고정이다.
  합성곱(입력, 입력채널, 입력크기, 층이름) {
    const 무게 = this.층[층이름 + ".weight"];
    const 치우침 = this.층[층이름 + ".bias"].값;
    const 출력채널 = 무게.모양[0];
    const 출력크기 = 입력크기 - 2;
    const 출력 = new Float32Array(출력채널 * 출력크기 * 출력크기);
    const 무게값 = 무게.값;

    for (let 출채널 = 0; 출채널 < 출력채널; 출채널++) {
      const 출채널_시작 = 출채널 * 출력크기 * 출력크기;
      const 무게_출채널_시작 = 출채널 * 입력채널 * 9;

      for (let y = 0; y < 출력크기; y++) {
        for (let x = 0; x < 출력크기; x++) {
          let 합 = 치우침[출채널];

          for (let 입채널 = 0; 입채널 < 입력채널; 입채널++) {
            const 입력_시작 = 입채널 * 입력크기 * 입력크기;
            const 무게_시작 = 무게_출채널_시작 + 입채널 * 9;

            for (let ky = 0; ky < 3; ky++) {
              const 행_시작 = 입력_시작 + (y + ky) * 입력크기 + x;
              const 무게행 = 무게_시작 + ky * 3;
              합 += 입력[행_시작] * 무게값[무게행]
                  + 입력[행_시작 + 1] * 무게값[무게행 + 1]
                  + 입력[행_시작 + 2] * 무게값[무게행 + 2];
            }
          }
          // ReLU를 여기서 함께 적용한다
          출력[출채널_시작 + y * 출력크기 + x] = 합 > 0 ? 합 : 0;
        }
      }
    }
    return 출력;
  }

  // 2x2 최대 풀링
  최대풀링(입력, 채널수, 입력크기) {
    const 출력크기 = Math.floor(입력크기 / 2);
    const 출력 = new Float32Array(채널수 * 출력크기 * 출력크기);

    for (let 채널 = 0; 채널 < 채널수; 채널++) {
      const 입력_시작 = 채널 * 입력크기 * 입력크기;
      const 출력_시작 = 채널 * 출력크기 * 출력크기;

      for (let y = 0; y < 출력크기; y++) {
        for (let x = 0; x < 출력크기; x++) {
          const 위 = 입력_시작 + (y * 2) * 입력크기 + x * 2;
          const 아래 = 위 + 입력크기;
          const 최대값 = Math.max(입력[위], 입력[위 + 1], 입력[아래], 입력[아래 + 1]);
          출력[출력_시작 + y * 출력크기 + x] = 최대값;
        }
      }
    }
    return 출력;
  }

  // 완전연결 계층. relu가 참이면 ReLU까지 적용한다.
  완전연결(입력, 층이름, relu) {
    const 무게 = this.층[층이름 + ".weight"];
    const 치우침 = this.층[층이름 + ".bias"].값;
    const 출력수 = 무게.모양[0];
    const 입력수 = 무게.모양[1];
    const 무게값 = 무게.값;
    const 출력 = new Float32Array(출력수);

    for (let i = 0; i < 출력수; i++) {
      let 합 = 치우침[i];
      const 행_시작 = i * 입력수;
      for (let j = 0; j < 입력수; j++) {
        합 += 입력[j] * 무게값[행_시작 + j];
      }
      출력[i] = relu && 합 < 0 ? 0 : 합;
    }
    return 출력;
  }

  // 로그 소프트맥스. 파이썬의 F.log_softmax와 같은 값을 내야 한다.
  로그소프트맥스(입력) {
    let 최대 = -Infinity;
    for (const 값 of 입력) if (값 > 최대) 최대 = 값;

    let 합 = 0;
    for (const 값 of 입력) 합 += Math.exp(값 - 최대);
    const 로그합 = Math.log(합) + 최대;

    return Float32Array.from(입력, (값) => 값 - 로그합);
  }

  // 정규화까지 끝난 28x28 입력(Float32Array 784개)을 받아 로그 확률 10개를 돌려준다
  추론(입력) {
    let 출력 = this.합성곱(입력, 1, 28, "합성곱1");    // 32 x 26 x 26
    출력 = this.합성곱(출력, 32, 26, "합성곱2");        // 64 x 24 x 24
    출력 = this.최대풀링(출력, 64, 24);                 // 64 x 12 x 12
    출력 = this.완전연결(출력, "완전연결1", true);      // 128
    출력 = this.완전연결(출력, "완전연결2", false);     // 10
    return this.로그소프트맥스(출력);
  }

  // 0~255 밝기값 784개를 받아 정규화한 뒤 추론한다
  화소로_추론(화소) {
    const 입력 = new Float32Array(784);
    for (let i = 0; i < 784; i++) {
      입력[i] = (화소[i] / 255 - this.평균) / this.표준편차;
    }
    return this.추론(입력);
  }
}
