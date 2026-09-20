// 생성: 2026-09-20 19:14 (KST)
// 마우스와 손가락으로 숫자를 그리는 캔버스를 다룬다.
// 데스크톱 버전과 같이 검은 바탕에 흰색으로, 끝이 둥근 굵은 선을 그린다.

export class 그림판 {
  constructor(캔버스, 붓굵기 = 18) {
    this.캔버스 = 캔버스;
    this.맥락 = 캔버스.getContext("2d", { willReadFrequently: true });
    this.붓굵기 = 붓굵기;
    this.그리는중 = false;
    this.이전점 = null;
    this.그림그린뒤 = null;   // 한 획을 마칠 때마다 부를 함수

    this.지우기();
    this.사건연결();
  }

  지우기() {
    this.맥락.fillStyle = "#000000";
    this.맥락.fillRect(0, 0, this.캔버스.width, this.캔버스.height);
    this.이전점 = null;
  }

  // 화면상의 좌표를 캔버스 내부 좌표로 바꾼다 (CSS로 크기가 달라져도 맞게)
  좌표구하기(사건) {
    const 상자 = this.캔버스.getBoundingClientRect();
    const 점 = 사건.touches ? 사건.touches[0] : 사건;
    return {
      x: (점.clientX - 상자.left) * (this.캔버스.width / 상자.width),
      y: (점.clientY - 상자.top) * (this.캔버스.height / 상자.height),
    };
  }

  선그리기(x, y) {
    const 맥락 = this.맥락;
    맥락.strokeStyle = "#ffffff";
    맥락.fillStyle = "#ffffff";
    맥락.lineWidth = this.붓굵기;
    맥락.lineCap = "round";
    맥락.lineJoin = "round";

    const 이전 = this.이전점 ?? { x, y };
    맥락.beginPath();
    맥락.moveTo(이전.x, 이전.y);
    맥락.lineTo(x, y);
    맥락.stroke();

    // 점 하나만 찍었을 때도 보이도록 원을 그린다
    맥락.beginPath();
    맥락.arc(x, y, this.붓굵기 / 2, 0, Math.PI * 2);
    맥락.fill();

    this.이전점 = { x, y };
  }

  사건연결() {
    const 시작 = (사건) => {
      사건.preventDefault();
      this.그리는중 = true;
      const { x, y } = this.좌표구하기(사건);
      this.이전점 = { x, y };
      this.선그리기(x, y);
    };

    const 이동 = (사건) => {
      if (!this.그리는중) return;
      사건.preventDefault();
      const { x, y } = this.좌표구하기(사건);
      this.선그리기(x, y);
    };

    const 끝 = (사건) => {
      if (!this.그리는중) return;
      사건.preventDefault();
      this.그리는중 = false;
      this.이전점 = null;
      if (this.그림그린뒤) this.그림그린뒤();
    };

    this.캔버스.addEventListener("mousedown", 시작);
    this.캔버스.addEventListener("mousemove", 이동);
    window.addEventListener("mouseup", 끝);
    this.캔버스.addEventListener("touchstart", 시작, { passive: false });
    this.캔버스.addEventListener("touchmove", 이동, { passive: false });
    this.캔버스.addEventListener("touchend", 끝, { passive: false });
  }
}
