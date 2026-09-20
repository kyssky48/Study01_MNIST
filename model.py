"""MNIST 손글씨 숫자 인식용 CNN 모델 정의.

학습(train.py)과 추론(draw_app.py)에서 같은 구조를 쓰기 위해 별도 파일로 분리했다.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class 숫자인식CNN(nn.Module):
    """28x28 흑백 이미지를 입력받아 0~9 중 하나로 분류하는 합성곱 신경망."""

    def __init__(self):
        super().__init__()
        # 합성곱 계층: 1채널(흑백) -> 32채널 -> 64채널
        self.합성곱1 = nn.Conv2d(1, 32, kernel_size=3)   # 28x28 -> 26x26
        self.합성곱2 = nn.Conv2d(32, 64, kernel_size=3)  # 26x26 -> 24x24
        # 과적합을 줄이기 위한 드롭아웃
        self.드롭아웃1 = nn.Dropout(0.25)
        self.드롭아웃2 = nn.Dropout(0.5)
        # 완전연결 계층: 풀링 뒤 12x12x64 = 9216차원
        self.완전연결1 = nn.Linear(9216, 128)
        self.완전연결2 = nn.Linear(128, 10)

    def forward(self, 입력):
        출력 = F.relu(self.합성곱1(입력))
        출력 = F.relu(self.합성곱2(출력))
        출력 = F.max_pool2d(출력, 2)      # 24x24 -> 12x12
        출력 = self.드롭아웃1(출력)
        출력 = torch.flatten(출력, 1)     # (배치, 9216)
        출력 = F.relu(self.완전연결1(출력))
        출력 = self.드롭아웃2(출력)
        출력 = self.완전연결2(출력)
        # 로그 확률을 반환한다 (손실 함수로 nll_loss 사용)
        return F.log_softmax(출력, dim=1)
