"""MNIST 데이터셋으로 CNN을 학습하고 가중치를 mnist_cnn.pt로 저장한다.

학습 데이터에는 무작위 변형(회전·이동·확대축소)을 주고, 에폭마다 학습률을 줄인다.
평가 정확도가 가장 높았던 시점의 가중치만 저장한다.

사용법:
    python train.py              # 기본 12 에폭 학습
    python train.py --에폭 20    # 에폭 수 지정
"""

import argparse
from pathlib import Path

import torch
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import StepLR
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from model import 숫자인식CNN

# 가중치를 저장할 파일 경로
가중치_파일 = Path(__file__).parent / "mnist_cnn.pt"
# MNIST 데이터셋을 내려받을 폴더
데이터_폴더 = Path(__file__).parent / "data"

# MNIST 전체 평균/표준편차 (정규화에 사용하는 관례적인 값)
평균 = 0.1307
표준편차 = 0.3081


def 데이터로더_만들기(배치크기: int, 평가_배치크기: int):
    """MNIST 학습용/평가용 데이터로더를 만들어 돌려준다.

    학습용에만 무작위 변형(증강)을 넣어 일반화 성능을 높인다.
    평가용에는 넣지 않는다 — 정확도를 정직하게 재기 위해서다.
    """
    학습_변환 = transforms.Compose([
        # 살짝 회전·이동·확대축소해서 매 에폭 조금씩 다른 글씨를 보여 준다
        transforms.RandomAffine(degrees=10, translate=(0.1, 0.1), scale=(0.9, 1.1)),
        transforms.ToTensor(),                    # 0~255 → 0.0~1.0 텐서
        transforms.Normalize((평균,), (표준편차,)),  # 정규화
    ])
    평가_변환 = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((평균,), (표준편차,)),
    ])
    학습_데이터 = datasets.MNIST(데이터_폴더, train=True, download=True, transform=학습_변환)
    평가_데이터 = datasets.MNIST(데이터_폴더, train=False, download=True, transform=평가_변환)

    학습_로더 = DataLoader(학습_데이터, batch_size=배치크기, shuffle=True)
    평가_로더 = DataLoader(평가_데이터, batch_size=평가_배치크기, shuffle=False)
    return 학습_로더, 평가_로더


def 한_에폭_학습(모델, 장치, 학습_로더, 최적화기, 에폭_번호, 기록_간격=100):
    """학습 데이터를 한 바퀴 돌면서 가중치를 갱신한다."""
    모델.train()  # 드롭아웃을 켠다
    for 묶음_번호, (이미지, 정답) in enumerate(학습_로더):
        이미지, 정답 = 이미지.to(장치), 정답.to(장치)
        최적화기.zero_grad()              # 이전 기울기 초기화
        예측 = 모델(이미지)
        손실 = F.nll_loss(예측, 정답)     # 로그 확률이므로 NLL 손실 사용
        손실.backward()                   # 역전파
        최적화기.step()                   # 가중치 갱신

        if 묶음_번호 % 기록_간격 == 0:
            진행률 = 100.0 * 묶음_번호 / len(학습_로더)
            print(f"에폭 {에폭_번호} [{진행률:5.1f}%] 손실: {손실.item():.4f}")


def 평가(모델, 장치, 평가_로더) -> float:
    """평가 데이터로 정확도를 계산해 돌려준다(%)."""
    모델.eval()  # 드롭아웃을 끈다
    총_손실 = 0.0
    맞힌_개수 = 0
    with torch.no_grad():  # 평가 중에는 기울기를 계산하지 않는다
        for 이미지, 정답 in 평가_로더:
            이미지, 정답 = 이미지.to(장치), 정답.to(장치)
            예측 = 모델(이미지)
            총_손실 += F.nll_loss(예측, 정답, reduction="sum").item()
            예측_숫자 = 예측.argmax(dim=1)
            맞힌_개수 += 예측_숫자.eq(정답).sum().item()

    전체_개수 = len(평가_로더.dataset)
    평균_손실 = 총_손실 / 전체_개수
    정확도 = 100.0 * 맞힌_개수 / 전체_개수
    print(f"[평가] 평균 손실: {평균_손실:.4f}, 정확도: {맞힌_개수}/{전체_개수} ({정확도:.2f}%)")
    return 정확도


def main():
    파서 = argparse.ArgumentParser(description="MNIST 손글씨 숫자 인식 CNN 학습")
    파서.add_argument("--에폭", type=int, default=12, help="학습 반복 횟수 (기본 12)")
    파서.add_argument("--배치크기", type=int, default=64, help="학습 배치 크기 (기본 64)")
    파서.add_argument("--평가배치크기", type=int, default=1000, help="평가 배치 크기 (기본 1000)")
    파서.add_argument("--학습률", type=float, default=1e-3, help="학습률 (기본 0.001)")
    파서.add_argument("--감쇠", type=float, default=0.7,
                      help="에폭마다 학습률에 곱할 값 (기본 0.7)")
    설정 = 파서.parse_args()

    # GPU가 있으면 GPU를, 없으면 CPU를 쓴다
    장치 = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"사용 장치: {장치}")

    학습_로더, 평가_로더 = 데이터로더_만들기(설정.배치크기, 설정.평가배치크기)

    모델 = 숫자인식CNN().to(장치)
    최적화기 = optim.Adam(모델.parameters(), lr=설정.학습률)
    # 에폭이 지날수록 학습률을 줄여 후반부에 미세하게 조정한다
    스케줄러 = StepLR(최적화기, step_size=1, gamma=설정.감쇠)

    최고_정확도 = 0.0
    for 에폭_번호 in range(1, 설정.에폭 + 1):
        한_에폭_학습(모델, 장치, 학습_로더, 최적화기, 에폭_번호)
        정확도 = 평가(모델, 장치, 평가_로더)
        스케줄러.step()

        # 지금까지 가장 좋은 성적일 때만 가중치를 저장한다
        if 정확도 > 최고_정확도:
            최고_정확도 = 정확도
            torch.save(모델.state_dict(), 가중치_파일)
            print(f"  → 최고 기록 갱신, 가중치 저장: {가중치_파일.name} ({정확도:.2f}%)")

    print(f"학습 종료. 최고 정확도: {최고_정확도:.2f}%")
    print(f"저장된 가중치: {가중치_파일}")


if __name__ == "__main__":
    main()
