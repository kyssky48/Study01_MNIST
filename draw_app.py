"""마우스로 숫자를 그리면 학습된 CNN이 인식해 주는 프로그램.

사용법:
    python draw_app.py

검은 배경 위에 흰색으로 숫자를 그린 뒤 [인식] 버튼을 누르거나,
마우스 버튼을 떼면 자동으로 인식 결과가 표시된다.
"""

import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

from model import 숫자인식CNN

가중치_파일 = Path(__file__).parent / "mnist_cnn.pt"
아이콘_파일 = Path(__file__).parent / "icon.ico"

# 윈도우 작업 표시줄이 이 앱을 파이썬이 아닌 독립된 프로그램으로 보게 하는 식별자.
# 바로가기에도 같은 값을 넣어 두면 고정한 아이콘과 실행 중인 창이 하나로 묶인다.
앱_식별자 = "kyssk.MNIST.HandwritingRecognizer"

# 그림판 크기(화면에 보이는 크기)와 붓 굵기
캔버스_크기 = 280
붓_굵기 = 18

# 학습할 때 쓴 정규화 값과 같아야 한다
평균 = 0.1307
표준편차 = 0.3081


def 모델_불러오기(장치):
    """저장된 가중치를 읽어 추론 준비가 된 모델을 돌려준다."""
    if not 가중치_파일.exists():
        안내 = (f"학습된 가중치 파일이 없습니다:\n{가중치_파일}\n\n"
                "명령 프롬프트에서 아래를 먼저 실행하세요.\n\n"
                "    python train.py")
        print(안내)
        # 바로가기(pythonw.exe)로 실행하면 콘솔이 없어 print가 보이지 않는다.
        # 그래서 대화상자로도 알려 준다.
        숨긴_창 = tk.Tk()
        숨긴_창.withdraw()
        messagebox.showerror("손글씨 숫자 인식", 안내)
        숨긴_창.destroy()
        sys.exit(1)

    모델 = 숫자인식CNN().to(장치)
    모델.load_state_dict(torch.load(가중치_파일, map_location=장치))
    모델.eval()  # 추론 모드 (드롭아웃 끔)
    return 모델


def 전처리(그림: Image.Image) -> torch.Tensor | None:
    """사용자가 그린 그림을 MNIST와 같은 형식(28x28)으로 바꾼다.

    MNIST는 숫자를 20x20 안에 맞춰 넣고, 무게중심을 28x28 한가운데에 둔다.
    같은 방식으로 맞춰 주어야 인식률이 높다.
    아무것도 그리지 않았으면 None을 돌려준다.
    """
    배열 = np.array(그림, dtype=np.float32)

    # 글씨가 있는 영역(0이 아닌 픽셀)의 경계 상자를 찾는다
    좌표 = np.argwhere(배열 > 0)
    if 좌표.size == 0:
        return None
    (위, 왼쪽), (아래, 오른쪽) = 좌표.min(axis=0), 좌표.max(axis=0) + 1
    잘라낸 = Image.fromarray(배열[위:아래, 왼쪽:오른쪽].astype(np.uint8))

    # 긴 변을 20픽셀에 맞춰 비율을 유지한 채 축소한다
    너비, 높이 = 잘라낸.size
    if 너비 > 높이:
        새_너비, 새_높이 = 20, max(1, round(높이 * 20 / 너비))
    else:
        새_높이, 새_너비 = 20, max(1, round(너비 * 20 / 높이))
    축소 = 잘라낸.resize((새_너비, 새_높이), Image.LANCZOS)

    # 28x28 검은 바탕 가운데에 붙인다
    바탕 = Image.new("L", (28, 28), 0)
    바탕.paste(축소, ((28 - 새_너비) // 2, (28 - 새_높이) // 2))

    # 무게중심이 가운데(13.5, 13.5)에 오도록 평행 이동한다
    화소 = np.array(바탕, dtype=np.float32)
    총합 = 화소.sum()
    if 총합 > 0:
        y좌표, x좌표 = np.indices(화소.shape)
        중심_x = (x좌표 * 화소).sum() / 총합
        중심_y = (y좌표 * 화소).sum() / 총합
        이동_x = round(13.5 - 중심_x)
        이동_y = round(13.5 - 중심_y)
        화소 = np.roll(화소, (이동_y, 이동_x), axis=(0, 1))

    # 0~1로 만든 뒤 학습 때와 같은 방식으로 정규화하고 (1, 1, 28, 28) 모양으로
    정규화 = (화소 / 255.0 - 평균) / 표준편차
    return torch.from_numpy(정규화).unsqueeze(0).unsqueeze(0)


class 손글씨_인식_앱:
    """tkinter 창에 그림판과 인식 결과를 보여 주는 앱."""

    def __init__(self, 창, 모델, 장치):
        self.모델 = 모델
        self.장치 = 장치
        self.창 = 창
        창.title("손글씨 숫자 인식")
        창.resizable(False, False)
        # 창 왼쪽 위와 작업 표시줄에 표시될 아이콘
        if 아이콘_파일.exists():
            try:
                창.iconbitmap(str(아이콘_파일))
            except tk.TclError:
                pass  # 아이콘을 못 읽어도 앱은 그대로 동작한다

        # 화면에 보이는 그림판
        self.캔버스 = tk.Canvas(창, width=캔버스_크기, height=캔버스_크기,
                                bg="black", cursor="crosshair")
        self.캔버스.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # 화면과 똑같이 그려 두었다가 인식에 쓰는 내부 이미지
        self.그림 = Image.new("L", (캔버스_크기, 캔버스_크기), 0)
        self.붓 = ImageDraw.Draw(self.그림)
        self.이전_점 = None

        self.캔버스.bind("<Button-1>", self.누름)
        self.캔버스.bind("<B1-Motion>", self.끌기)
        self.캔버스.bind("<ButtonRelease-1>", self.뗌)

        self.결과_라벨 = tk.Label(창, text="숫자를 그려 보세요", font=("맑은 고딕", 20))
        self.결과_라벨.grid(row=1, column=0, columnspan=2)

        self.확률_라벨 = tk.Label(창, text="", font=("맑은 고딕", 10), justify="left")
        self.확률_라벨.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 6))

        tk.Button(창, text="인식", width=12, command=self.인식).grid(
            row=3, column=0, pady=(0, 10))
        tk.Button(창, text="지우기", width=12, command=self.지우기).grid(
            row=3, column=1, pady=(0, 10))

    def 누름(self, 사건):
        self.이전_점 = (사건.x, 사건.y)
        self.선_그리기(사건.x, 사건.y)

    def 끌기(self, 사건):
        self.선_그리기(사건.x, 사건.y)

    def 뗌(self, _사건):
        self.이전_점 = None
        self.인식()  # 마우스를 떼면 바로 인식

    def 선_그리기(self, x, y):
        """화면과 내부 이미지에 같은 선을 그린다."""
        반지름 = 붓_굵기 / 2
        if self.이전_점 is None:
            self.이전_점 = (x, y)
        이전_x, 이전_y = self.이전_점

        self.캔버스.create_line(이전_x, 이전_y, x, y, fill="white",
                                width=붓_굵기, capstyle=tk.ROUND, smooth=True)
        self.붓.line([이전_x, 이전_y, x, y], fill=255, width=붓_굵기)
        # 선 끝을 둥글게 만들어 화면과 내부 이미지 모양을 맞춘다
        self.붓.ellipse([x - 반지름, y - 반지름, x + 반지름, y + 반지름], fill=255)
        self.이전_점 = (x, y)

    def 지우기(self):
        self.캔버스.delete("all")
        self.붓.rectangle([0, 0, 캔버스_크기, 캔버스_크기], fill=0)
        self.이전_점 = None
        self.결과_라벨.config(text="숫자를 그려 보세요")
        self.확률_라벨.config(text="")

    def 인식(self):
        입력 = 전처리(self.그림)
        if 입력 is None:
            self.결과_라벨.config(text="그림이 비어 있습니다")
            self.확률_라벨.config(text="")
            return

        with torch.no_grad():
            출력 = self.모델(입력.to(self.장치))
            확률 = 출력.exp().squeeze(0).cpu().numpy()  # 로그 확률 → 확률

        예측_숫자 = int(확률.argmax())
        self.결과_라벨.config(
            text=f"예측: {예측_숫자}   (확신도 {확률[예측_숫자] * 100:.1f}%)")

        # 확률이 높은 순서대로 3개를 함께 보여 준다
        상위 = 확률.argsort()[::-1][:3]
        self.확률_라벨.config(
            text="  ".join(f"{숫자}: {확률[숫자] * 100:5.1f}%" for 숫자 in 상위))


def 작업표시줄_식별자_설정():
    """윈도우에서 이 앱이 파이썬과 따로 묶이도록 식별자를 등록한다.

    이걸 해야 작업 표시줄에 고정한 바로가기와 실행 중인 창이 같은 아이콘으로 합쳐진다.
    윈도우가 아니거나 실패해도 앱 동작에는 지장이 없다.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(앱_식별자)
    except Exception:
        pass


def main():
    작업표시줄_식별자_설정()
    장치 = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    모델 = 모델_불러오기(장치)

    창 = tk.Tk()
    손글씨_인식_앱(창, 모델, 장치)
    창.mainloop()


if __name__ == "__main__":
    main()
