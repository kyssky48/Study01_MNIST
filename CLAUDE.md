# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

손글씨로 쓴 숫자를 인식하는 PyTorch CNN. MNIST로 학습하고, tkinter 그림판에 마우스로 그린 숫자를 실시간으로 인식한다. Windows 데스크톱 앱으로 실행하는 것을 전제로 한다.

## 코드 규칙

**모든 식별자와 주석이 한글이다.** 함수명(`한_에폭_학습`), 변수명(`가중치_파일`), 클래스명(`숫자인식CNN`), argparse 인자(`--에폭`)까지 전부 한글이다. 코드를 추가·수정할 때 이 규칙을 지킨다. PyTorch API 이름과 파일명만 영문이다.

## 자주 쓰는 명령

```bash
python train.py                  # 기본 12 에폭 학습 → mnist_cnn.pt 저장
python train.py --에폭 20        # 에폭 수 지정 (--배치크기 --학습률 --감쇠도 지원)
python draw_app.py               # 손글씨 인식 앱 실행
python make_icon.py              # icon.ico 재생성
powershell -ExecutionPolicy Bypass -File create_shortcut.ps1   # 바탕화면 바로가기 재생성
```

Git Bash에서 한글 출력이 깨지면 `PYTHONIOENCODING=utf-8`을 앞에 붙인다. 백그라운드로 학습을 돌리면 파이썬이 stdout을 버퍼링해서 중간 로그가 보이지 않고 종료 시 한꺼번에 나온다.

## 구조

| 파일 | 역할 |
|---|---|
| `model.py` | `숫자인식CNN` 정의. 학습과 추론이 공유하는 유일한 구조 정의 |
| `train.py` | 데이터로더 구성 → 학습 → 평가 → 최고 기록 시점 가중치 저장 |
| `draw_app.py` | tkinter GUI + 그림 → 28×28 전처리 + 추론 |
| `make_icon.py` | PIL로 다중 해상도 `icon.ico` 생성 |
| `create_shortcut.ps1` | pythonw.exe 대상 바로가기 생성 + AppUserModelID 삽입 |

## 파일 간 반드시 맞춰야 하는 값

이 프로젝트의 버그는 대부분 아래 중복된 값이 어긋나면서 생긴다.

1. **정규화 상수** — `평균 = 0.1307`, `표준편차 = 0.3081`이 `train.py:29-30`과 `draw_app.py:33-34`에 각각 정의돼 있다. 한쪽만 바꾸면 학습과 추론의 입력 분포가 달라져 인식률이 조용히 무너진다.
2. **모델 구조** — `mnist_cnn.pt`는 `state_dict`만 저장한다. `model.py`의 레이어를 바꾸면 기존 가중치 파일은 로드에 실패하므로 재학습이 필요하다.
3. **앱 식별자** — `draw_app.py:26`의 `앱_식별자`와 `create_shortcut.ps1:21`의 `$앱식별자`가 같아야 작업 표시줄에 고정한 아이콘과 실행 중인 창이 하나로 묶인다.

## 학습 설계

- 학습 데이터에만 `RandomAffine(회전 ±10°, 이동 10%, 확대축소 0.9~1.1)` 증강을 적용한다. 평가 데이터에는 적용하지 않는다 — 정확도를 정직하게 재기 위해서다.
- `StepLR(step_size=1, gamma=0.7)`로 에폭마다 학습률을 줄인다.
- 매 에폭 평가 후 **최고 정확도를 갱신할 때만** `mnist_cnn.pt`를 덮어쓴다. 마지막 에폭이 최고가 아닐 수 있다.
- 현재 기준선: 12 에폭 / CPU 약 25분 / 테스트 정확도 **99.33%**. 성능을 건드리는 변경을 했다면 이 숫자와 비교한다.

## 추론 전처리

`draw_app.py`의 `전처리()`는 280×280 캔버스 그림을 MNIST와 같은 형식으로 정규화한다: 글씨 영역 경계 잘라내기 → 비율 유지한 채 20×20으로 축소 → 28×28 가운데 배치 → **무게중심을 (13.5, 13.5)로 평행 이동**. 학습 데이터와 입력 형식을 맞추는 단계이므로 함부로 생략하지 않는다. 현재 가중치 기준으로 이 경로의 정확도는 99.6%다(MNIST 테스트 이미지를 280×280으로 확대해 통과시킨 500장 측정). 아무것도 그리지 않으면 `None`을 돌려준다.

## Windows 관련 제약

- 바로가기는 콘솔 창을 없애려고 `python.exe`가 아닌 **`pythonw.exe`** 를 실행한다. 따라서 `draw_app.py`의 `print`는 사용자에게 보이지 않는다. 사용자가 알아야 할 오류는 `messagebox`로 띄운다(가중치 파일 누락 안내가 그 예다).
- `create_shortcut.ps1`은 UTF-8 BOM으로 저장해야 한다. PowerShell 5.1은 BOM이 없으면 한글 주석을 ANSI로 읽어 깨뜨린다.
- 바로가기에 AppUserModelID를 넣는 데 `WScript.Shell`로는 불가능해 `IPropertyStore` COM 인터페이스를 `Add-Type`으로 직접 정의해 쓴다. `propsys.dll`의 `InitPropVariantFromString`은 이 환경에서 내보내지 않으므로 PROPVARIANT를 직접 구성한다.

## 웹 버전 (`docs/`)

`docs/`는 GitHub Pages로 배포되는 웹 앱이며, 같은 모델을 **외부 라이브러리 없이 순수 자바스크립트로** 다시 구현한 것이다. 파이썬 쪽과 다음이 짝을 이룬다.

| 파이썬 | 자바스크립트 |
|---|---|
| `model.py`의 `숫자인식CNN` | `docs/모델.js`의 `숫자인식모델` |
| `draw_app.py`의 `전처리()` | `docs/전처리.js`의 `전처리()` |
| `draw_app.py`의 그림판 | `docs/그림판.js` |

- 한쪽 구조를 바꾸면 다른 쪽도 함께 고쳐야 한다. `모델.js`의 `층_순서`는 `export_weights.py`의 `층_순서`와 순서가 같아야 한다.
- 가중치를 재학습했으면 `python export_weights.py`로 `docs/가중치.bin`과 `docs/가중치정보.json`, `docs/검증데이터.json`을 다시 내보내야 한다. 내보내지 않으면 웹 버전만 옛 모델로 동작한다.
- 전처리의 축소 단계는 파이썬이 PIL LANCZOS, 자바스크립트가 영역 평균이라 화소값이 완전히 같지는 않다. 예측 결과는 일치하는 것으로 확인했다.

## 검증

테스트 프레임워크가 없다. 변경 후 확인은 다음으로 한다.

- 학습 관련 변경: `python train.py --에폭 1`로 파이프라인이 도는지 본 뒤, 전체 학습으로 정확도를 기준선과 비교한다.
- 추론/전처리 변경: 저장된 가중치를 불러와 MNIST 테스트셋을 다시 평가하고, 테스트 이미지를 캔버스 크기(280×280)로 확대해 `전처리()`에 통과시킨 결과도 함께 확인한다.
- GUI 변경: `창.after()`로 일정 시간 뒤 캡처·종료하는 스크립트를 쓰면 창을 띄우고도 자동으로 검증할 수 있다.
- 웹 버전 변경: `python -m http.server 8765 --directory docs`로 띄운 뒤 `검증.html`을 연다. PyTorch 출력값과의 최대 오차(1e-3 미만)와 전체 경로 정답률을 자동으로 판정한다. `file://`로 열면 ES 모듈과 fetch가 막히므로 반드시 서버로 연다.

## 저장소 상태

- 원격은 https://github.com/kyssky48/Study01_MNIST (공개). GitHub Pages가 `main` 브랜치의 `docs/` 폴더를 배포한다.
- `.gitignore`가 `data/`(torchvision이 내려받는 MNIST 원본 약 64MB), `__pycache__/`, `.superpowers/`를 제외한다. `mnist_cnn.pt`와 `docs/가중치.bin`은 일부러 추적한다 — 받는 사람이 학습 없이 바로 쓸 수 있게 하기 위해서다.
- 사용자 지침상 `main`에 바로 커밋하지 않고 작업 브랜치를 만든다. 커밋과 push는 사용자가 요청할 때만 한다.
- `requirements.txt`가 없다. 의존성은 `torch`, `torchvision`, `pillow`, `numpy`이며 CPU 휠로 설치돼 있다(`--index-url https://download.pytorch.org/whl/cpu`).
