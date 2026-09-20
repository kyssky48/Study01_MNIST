# 생성: 2026-09-20 19:14 (KST)
"""학습된 mnist_cnn.pt를 웹 버전이 읽을 수 있는 형식으로 내보낸다.

만드는 파일:
    docs/가중치.bin       — 모든 가중치를 float32 리틀엔디언으로 이어 붙인 것
    docs/가중치정보.json  — 각 층의 이름·모양·바이트 위치
    docs/검증데이터.json  — MNIST 테스트 이미지 50장과 PyTorch가 낸 출력값
                            (브라우저 결과가 파이썬과 같은지 대조하는 용도)

사용법:
    python export_weights.py
"""

import json
import struct
from pathlib import Path

import numpy as np
import torch
from torchvision import datasets

from model import 숫자인식CNN
from train import 평균, 표준편차, 데이터_폴더

내보낼_폴더 = Path(__file__).parent / "docs"
가중치_파일 = Path(__file__).parent / "mnist_cnn.pt"

# 웹에서 읽을 순서대로 층 이름을 적는다 (모델.js의 순서와 같아야 한다)
층_순서 = [
    "합성곱1.weight", "합성곱1.bias",
    "합성곱2.weight", "합성곱2.bias",
    "완전연결1.weight", "완전연결1.bias",
    "완전연결2.weight", "완전연결2.bias",
]

검증_장수 = 50


def 가중치_내보내기(상태):
    """가중치를 하나의 이진 파일로 이어 붙이고, 위치 정보를 돌려준다."""
    조각들 = []
    정보 = []
    현재_위치 = 0

    for 이름 in 층_순서:
        값 = 상태[이름].detach().cpu().numpy().astype(np.float32)
        평탄 = 값.reshape(-1)
        조각들.append(평탄.tobytes())
        정보.append({
            "이름": 이름,
            "모양": list(값.shape),
            "시작": 현재_위치,      # float32 개수 기준 위치
            "개수": int(평탄.size),
        })
        현재_위치 += int(평탄.size)

    (내보낼_폴더 / "가중치.bin").write_bytes(b"".join(조각들))

    설정 = {
        "설명": "MNIST 손글씨 숫자 인식 CNN 가중치 (float32 리틀엔디언)",
        "평균": 평균,
        "표준편차": 표준편차,
        "전체개수": 현재_위치,
        "층": 정보,
    }
    (내보낼_폴더 / "가중치정보.json").write_text(
        json.dumps(설정, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"가중치.bin: {현재_위치:,}개 float32 = {현재_위치 * 4:,} bytes")
    return 현재_위치


def 검증데이터_내보내기(모델):
    """테스트 이미지 몇 장과 그에 대한 PyTorch 출력값을 함께 저장한다.

    브라우저가 같은 입력으로 같은 숫자를 내는지 확인하는 데 쓴다.
    """
    데이터 = datasets.MNIST(데이터_폴더, train=False, download=False)
    항목들 = []

    for 번호 in range(검증_장수):
        원본, 정답 = 데이터[번호]
        화소 = np.array(원본, dtype=np.uint8)              # 28x28, 0~255
        정규화 = (화소.astype(np.float32) / 255.0 - 평균) / 표준편차
        입력 = torch.from_numpy(정규화).unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            출력 = 모델(입력).squeeze(0).numpy()            # 로그 확률 10개

        항목들.append({
            "정답": int(정답),
            "화소": 화소.reshape(-1).tolist(),              # 0~255 정수 784개
            "출력": [round(float(값), 6) for 값 in 출력],
        })

    (내보낼_폴더 / "검증데이터.json").write_text(
        json.dumps({"장수": 검증_장수, "항목": 항목들}, ensure_ascii=False),
        encoding="utf-8")
    print(f"검증데이터.json: {검증_장수}장")


def main():
    내보낼_폴더.mkdir(exist_ok=True)

    모델 = 숫자인식CNN()
    모델.load_state_dict(torch.load(가중치_파일, map_location="cpu"))
    모델.eval()

    상태 = 모델.state_dict()
    전체 = 가중치_내보내기(상태)
    검증데이터_내보내기(모델)

    # 내보낸 파일을 다시 읽어 원본과 같은지 확인한다
    복원 = np.frombuffer((내보낼_폴더 / "가중치.bin").read_bytes(), dtype="<f4")
    assert 복원.size == 전체, "크기가 맞지 않습니다"
    위치 = 0
    최대오차 = 0.0
    for 이름 in 층_순서:
        원본 = 상태[이름].detach().cpu().numpy().astype(np.float32).reshape(-1)
        조각 = 복원[위치:위치 + 원본.size]
        최대오차 = max(최대오차, float(np.abs(원본 - 조각).max()))
        위치 += 원본.size
    print(f"되읽기 검사: 최대 오차 {최대오차}")
    print("내보내기 완료:", 내보낼_폴더)


if __name__ == "__main__":
    main()
