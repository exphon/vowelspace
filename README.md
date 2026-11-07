# 🎙️ Vowel Space Visualizer

음성학 연구를 위한 모음 공간 및 포먼트 궤적 시각화 웹 애플리케이션입니다. 다양한 통계 분석 기능과 인터랙티브 시각화를 제공합니다.

## 📋 빠른 링크

- [자동 컬럼 감지 가이드](AUTO_COLUMN_DETECTION_GUIDE.md) - 다양한 데이터 형식 자동 인식 기능
- [문제 해결 가이드](TROUBLESHOOTING.md) - 일반적인 문제 해결 방법
- [구현 요약](IMPLEMENTATION_SUMMARY.md) - 기술적 구현 세부사항

## ✨ 주요 기능

### � 시각화 기능

- **정적 모음 공간 시각화**: F1과 F2 값을 기반으로 전통적인 모음 공간 플롯 생성
- **동적 포먼트 궤적 시각화**: 시간에 따른 포먼트 변화를 추적하고 시각화
- **타원 모음 공간**: 95% 신뢰 타원으로 모음 클러스터 표시
- **다층 그룹화**: 모음(vowel), 화자(speaker), 모국어(native_language)에 따른 자동 그룹화
- **포먼트 스케일 변환**: Hz, Bark, ERB, Mel 스케일 지원

### 📈 통계 분석 기능

- **기술통계**: 그룹별 평균, 표준편차, 최소/최대값
- **MANOVA**: 다변량 분산분석 (그룹 간 유의성 검정)
- **PCA**: 주성분 분석 (차원 축소 및 시각화)
- **LDA**: 선형 판별 분석 (그룹 분류 및 시각화)
- **쌍별 검정**: t-test와 Cohen's d 효과 크기
- **모음 공간 메트릭**: 면적, 중심점, 분산도 계산

### 📊 통계 그래프

- **박스플롯 (Box Plot)**: 분포와 이상치 시각화
- **바이올린 플롯 (Violin Plot)**: 확률밀도 포함 분포
- **밀도 플롯 (Density Plot)**: Gaussian KDE로 부드러운 분포 곡선
- **평균 비교 플롯**: 그룹별 평균값 및 표준 오차 비교
- **산점도 행렬 (Scatter Matrix)**: 변수 간 쌍별 관계 시각화

### 🤖 데이터 처리

- **자동 컬럼 감지**: 다양한 형식의 컬럼명을 지능적으로 인식하고 표준화 ([상세 가이드](AUTO_COLUMN_DETECTION_GUIDE.md))
- **다양한 입력 형식 지원**:
  - CSV/TXT/XLSX 파일 (F1, F2, vowel, time 등의 열 포함)
  - WAV 음성 파일 (자동 포먼트 추출)
  - WAV + TextGrid 파일 (레이블된 구간에서 포먼트 추출)
- **인터랙티브 그래프**: Plotly를 사용한 확대/축소, 데이터 포인트 확인 가능
- **그래프 다운로드**: PNG 형식으로 결과 저장

## 🚀 설치 방법

### 1. Python 환경 설정

Python 3.8 이상이 필요합니다. (현재 서버: Python 3.12, 가상환경 `.venv`)

```bash
cd /var/www/app/vowelspace
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 애플리케이션 실행

```bash
# 백그라운드 실행 (터미널을 닫아도 유지) - 권장
./run.sh

# 중지
./stop.sh

# 또는 직접 실행 (개발용)
.venv/bin/python app.py
```

포트와 디버그 모드는 환경변수로 바꿀 수 있습니다 (기본: 포트 5000, 디버그 OFF).

```bash
PORT=8080 ./run.sh          # 다른 포트로 실행
FLASK_DEBUG=1 .venv/bin/python app.py   # 디버그 모드 (개발용, 외부 공개 시 사용 금지)
```

브라우저에서 `http://localhost:5000` (외부에서는 `http://210.125.101.159:5000`) 을 열면 애플리케이션을 사용할 수 있습니다.

## 🌐 서비스 배포 (https://vowelspace.tyoon.net)

운영 서버에서는 `run.sh` 대신 systemd 서비스(gunicorn) + nginx 리버스 프록시로 실행합니다.
설정 파일은 `deploy/` 폴더에 있으며, 최초 1회 아래를 실행하면 서비스 등록, 인증서 발급, nginx 설정이 모두 적용됩니다.

```bash
sudo /var/www/app/vowelspace/deploy/setup.sh
```

| 파일 | 용도 |
|------|------|
| `deploy/vowelspace.service` | systemd 유닛 (gunicorn, 127.0.0.1:5000, 재부팅 시 자동 시작) |
| `deploy/nginx-vowelspace.conf` | nginx HTTPS 리버스 프록시 설정 |
| `deploy/nginx-vowelspace-bootstrap.conf` | 인증서 발급 전 임시 HTTP 설정 (setup.sh가 자동 사용) |

운영 중 관리 명령:

```bash
sudo systemctl status vowelspace     # 상태
sudo systemctl restart vowelspace    # 코드 수정 후 재시작
sudo journalctl -u vowelspace -f     # 로그
```

> 서비스가 등록된 뒤에는 `./run.sh`가 자동으로 `sudo systemctl restart vowelspace`를 실행하고, `./stop.sh`는 `sudo systemctl stop vowelspace`를 실행합니다. 서비스가 없을 때만 nohup 방식으로 직접 띄웁니다.

## 🤖 자동 컬럼 감지

이 도구는 **지능형 컬럼 감지** 기능을 제공합니다. 다양한 형식의 데이터 파일에서 자동으로 필요한 컬럼을 찾아냅니다.

### 감지 가능한 컬럼 패턴

| 표준 컬럼명 | 인식되는 이름 예시 |
|------------|------------------|
| `F1` | f1, F1, first_formant, formant_1, F1_Hz, f1_frequency, formant1 |
| `F2` | f2, F2, second_formant, formant_2, F2_Hz, f2_frequency, formant2 |
| `F3` | f3, F3, third_formant, formant_3, F3_Hz, f3_frequency |
| `vowel` | vowel, phone, phoneme, label, segment, ipa, sound, v, symbol |
| `speaker` | speaker, participant, subject, informant, talker, spk, id |
| `native_language` | native_language, L1, first_language, mother_tongue, lang |
| `time` | time, t, timestamp, time_point, midpoint, sec, seconds |
| `duration` | duration, dur, length, dur_s, dur_ms |
| `gender` | gender, sex, m/f |
| `age` | age, yrs |

### 감지 방법

시스템은 다음 3단계로 컬럼을 감지합니다:

1. **패턴 매칭**: 컬럼 이름이 알려진 정규표현식 패턴과 일치하는지 확인
2. **값 범위 분석**: 
   - F1: 200-1000 Hz 범위의 숫자
   - F2: 800-3000 Hz 범위의 숫자
   - F3: 1500-4000 Hz 범위의 숫자
3. **데이터 특성 분석**:
   - **모음**: 짧은 문자열 (1-5글자), IPA 기호 포함, 고유값 2-30개
   - **화자**: 카테고리형 데이터, 고유값 2-50개
   - **시간**: 순차적으로 증가하는 숫자값

### 예시

다음과 같은 다양한 형식의 데이터를 자동으로 인식합니다:

```csv
# 형식 1: 일반적인 형식
vowel,F1,F2,speaker,L1
i,300,2300,SP01,Korean

# 형식 2: 소문자 + 상세명
phone,f1_frequency,f2_frequency,participant,native_lang
i,300,2300,John,Korean

# 형식 3: 학술 형식
phoneme,first_formant,second_formant,subject_id,mother_tongue
i,300,2300,Subject_A,English

# 형식 4: 약어
v,f1,f2,spk,lang
i,300,2300,A,Korean
```

**모두 올바르게 감지되어 표준 컬럼명으로 자동 변환됩니다!**

### 감지 결과 확인

파일 업로드 후 "데이터 요약" 섹션에서 다음을 확인할 수 있습니다:

- 원본 컬럼명 → 표준화된 컬럼명 매핑
- 각 컬럼의 데이터 범위 및 통계
- 샘플 값 (카테고리형 컬럼의 경우)

### 예제

```
자동 감지된 컬럼:
  - F1: "first_formant" (범위: 250-850 Hz, 평균: 450 Hz)
  - F2: "second_formant" (범위: 800-2500 Hz, 평균: 1650 Hz)
  - vowel: "phone" (고유값 5개) [예: i, e, a, o, u]
  - speaker: "participant" (고유값 3개) [예: SP01, SP02, SP03]
```

## 📊 사용 방법

### 1. 기본 시각화

1. **파일 업로드**: CSV/XLSX/TXT 또는 WAV 파일 선택
2. **시각화 유형 선택**:
   - 정적 모음 공간 (Static Vowel Space)
   - 타원 모음 공간 (Vowel Space with Ellipses)
   - 동적 포먼트 궤적 (Dynamic Formant Trajectory)
3. **포먼트 스케일 선택**: Hz, Bark, ERB, Mel
4. **시각화하기** 버튼 클릭

### 2. 통계 분석

1. 기본 시각화 완료 후 **"📊 통계 분석 수행"** 버튼 클릭
2. 다음 탭에서 결과 확인:
   - **기술통계**: 그룹별 평균, 표준편차 등
   - **MANOVA**: 그룹 간 유의성 검정
   - **PCA**: 주성분 분석 및 시각화
   - **LDA**: 선형 판별 분석 및 분류
   - **통계 그래프**: 박스플롯, 바이올린 플롯, 밀도 플롯, 평균 비교, 산점도 행렬
   - **쌍별 검정**: 모든 그룹 쌍의 t-test 결과
   - **모음 공간 메트릭**: 면적, 분산도 등

### CSV/TXT/XLSX 파일 형식

파일에 다음 열이 포함되어야 합니다:

**필수 열:**
- `F1`: 첫 번째 포먼트 주파수 (Hz)
- `F2`: 두 번째 포먼트 주파수 (Hz)

**선택 열:**
- `vowel`: 모음 레이블 (예: i, e, a, o, u)
- `speaker`: 화자 ID (예: SP01, SP02)
- `native_language`: 모국어 (예: Korean, English)
- `time`: 시간 정보 (초 단위, 동적 시각화용)
- `duration`: 지속 시간 (초 단위)
- `gender`: 성별
- `age`: 나이

**예시 CSV (다중 화자, 다중 언어):**
```csv
vowel,F1,F2,speaker,native_language,time,duration
i,300,2300,SP01,Korean,0.5,0.15
i,310,2280,SP01,Korean,0.6,0.12
i,280,2350,SP02,English,0.5,0.18
e,450,2100,SP01,Korean,1.0,0.20
e,460,2090,SP02,English,1.0,0.22
a,700,1200,SP01,Korean,1.5,0.25
a,720,1180,SP02,English,1.5,0.28
```

**예시 CSV (간단한 형식):**
```csv
vowel,F1,F2,time
i,300,2300,0.5
i,310,2280,0.6
e,450,2100,1.0
e,460,2090,1.1
a,700,1200,1.5
```

**예시 TXT (탭 구분):**
```
vowel	F1	F2	time
i	300	2300	0.5
e	450	2100	1.0
a	700	1200	1.5
```

### WAV 파일 업로드

WAV 파일과 같은 이름의 TextGrid 파일을 함께 올리면 TextGrid에 레이블된 모음 구간에서 포먼트를 추출합니다.
(`spk01_t01.wav` ↔ `spk01_t01.TextGrid`). WAV마다 TextGrid가 하나씩 필요하며, TextGrid는 Praat 형식이고
모음 레이블이 포함된 interval tier가 있어야 합니다.

#### 포먼트 추출 방법 (WAV + TextGrid)

추출은 Praat(Parselmouth 라이브러리 경유)으로 수행되며 네 단계로 진행됩니다. 각 단계에서 *무엇을* 하고
*왜* 그렇게 하는지 설명합니다. 웹 화면의 "📖 TextGrid Formant Extraction Method" 블록과 같은 내용입니다.

**1단계 · 오디오 준비와 모음 구간 찾기**

1. **파일 짝 맞추기**: 확장자를 뺀 이름이 같은 WAV와 TextGrid를 한 쌍으로 묶습니다.
2. **파일명에서 화자 정보 읽기**: 첫 번째 `_` 또는 `-` 앞부분이 화자 ID, 두 번째 부분이 언어/그룹입니다.
   예: `fv01_kor_s01.wav` → 화자 `fv01`, 언어 `kor`. 같은 화자의 파일은 모두 함께 분석됩니다.
3. **16 kHz로 리샘플링**: 포먼트는 8 kHz 아래에 있으므로, 더 높은 샘플링 주파수는 LPC 분석에 잡음만 더합니다.
4. **모음 tier 선택**: tier 이름에 `vowel`, `phone`, `segment`가 들어간 첫 tier를 쓰고, 없으면 1번 tier를 씁니다.
5. **모음 구간만 남기기**: ARPABET(AH, IY1 …), IPA(ɪ, ʊ, ə …), 로마자 모음(a, e, i, o, u, eo …)을 모음으로 인식합니다.
   강세 숫자, 장음 기호, 발음 구별 부호는 무시하고, 자음과 묵음 구간은 건너뜁니다.

**2단계 · 화자별 포먼트 ceiling 결정**

**포먼트 ceiling**(Praat의 "maximum formant")은 포먼트 5개를 찾을 주파수 상한입니다. 화자의 F5 부근, 즉 성도
길이에 맞아야 합니다. Praat의 경험칙은 남성 5000 Hz, 여성 5500 Hz이지만 실제 화자는 편차가 큽니다. ceiling이
너무 낮으면 실제 포먼트 두 개가 하나로 병합되고, 너무 높으면 하나가 둘로 쪼개집니다. 두 오류 모두 F1/F2에
들어가 모음 공간을 왜곡합니다.

기본값인 **Auto per speaker**는 성별로 추정하지 않고 화자마다 최적 ceiling을 찾습니다.

1. **모음 구간만 잘라내기**: 모음 구간(앞뒤 50 ms 여유 포함)만 분석하고, 화자당 최대 30초 분량만 사용해 속도를 확보합니다.
2. **여러 ceiling 시도**: 4000–8000 Hz를 100 Hz 간격으로 41개 설정을 모두 시도합니다. 설정마다 Praat이 포먼트를
   다시 추적하고, 앱은 모든 모음 토큰의 F1–F4를 측정합니다(토큰 측정 방식은 3단계 참조).
3. **포먼트의 *안정성*으로 ceiling 점수화**: 점수가 낮을수록 추적 오류가 적다는 뜻입니다.
   - **F3–F4 stability**(기본; Feinberg 2019, OSF 사전등록 PDWCB): F3와 F4는 모음에 따라 거의 변하지 않으므로
     ceiling이 맞으면 모든 토큰에서 거의 일정해야 합니다. 점수 = 화자의 전체 토큰에 대한
     `var(20·log₁₀F3) + var(20·log₁₀F4)`. 모음당 토큰이 하나뿐이어도 동작합니다.
   - **Within-vowel F1–F2 stability**(Escudero, Boersma, Rauber & Bion 2009, JASA): 같은 모음을 반복하면 F1/F2가
     같아야 합니다. 점수 = 모음 내 pooled `var(20·log₁₀F1) + var(20·log₁₀F2)`. 토큰이 2개 이상인 모음이 하나는 있어야
     하며, 없으면 F3–F4 점수로 자동 대체됩니다.
   - **Both combined**: 두 점수의 합(둘 다 dB² 단위).
4. **불가능한 결과 기각**: 점수와 무관하게 다음 경우 그 ceiling을 버립니다. F3/F4가 없는 토큰이 20% 초과,
   F1 중앙값 1200 Hz 초과, F4 중앙값 2900 Hz 미만, F1·F2 병합(F2 − F1 < 150 Hz) 토큰이 20% 초과.
   포먼트가 일관되게 병합돼 분산이 낮아 보이는 경우를 막기 위한 장치입니다(Fast Track의 휴리스틱, Barreda 2021).
5. **미세 탐색**: 점수 곡선을 이웃 3개로 평활화해 가장 좋은 100 Hz 지점을 고르고, 그 ±100 Hz 구간을 20 Hz 간격으로
   다시 탐색합니다. 점수가 가장 낮은 ceiling을 채택하고, 유효한 것이 없으면 5500 Hz를 씁니다.
6. **보고**: 화자별로 채택된 ceiling, 사용된 기준, 토큰 수가 처리 후 Data Summary에 표시됩니다.
7. **선택: 모음별 ceiling**(`Optimize per: Speaker × vowel`): Escudero et al.(2009)은 같은 화자라도 모음에 따라 최적
   ceiling이 다르다고 보고했습니다(예: /u/ ≈ 4600 Hz, /i/ ≈ 5600 Hz). 혀 모양이 고차 포먼트를 바꾸기 때문입니다.
   이 옵션을 켜면 화자 ceiling을 구한 뒤, 토큰이 5개 이상인 모음 범주마다 그 모음의 토큰만으로 같은 점수를 계산해
   따로 탐색합니다. 탐색 범위는 화자 ceiling의 0.8–1.25배로 제한해 토큰 몇 개의 잡음이 극단값을 고르지 못하게 합니다.
   토큰이 부족한 모음은 화자 ceiling을 그대로 씁니다. CSV의 각 행에는 실제 사용된 ceiling이 기록됩니다.
   Escudero et al.은 모음당 토큰 20개를 썼습니다. 10개 미만이면 모음별 추정이 불안정하므로 같은 모음을 여러 번
   녹음한 자료에 쓰는 것을 권합니다.

동봉된 테스트 음성에서는 여성 화자 약 5600 Hz, 남성 화자 약 4800 Hz가 선택됐고, 남성 화자의 모음 내 F1/F2
산포는 고정 5500 Hz 대비 약 15–45% 줄었습니다.

기존 방식을 원하면 **Fixed 5500 Hz**, **Fixed 5000 Hz**, **Custom**을 선택합니다. 이 경우 2단계를 건너뛰고 모든
화자에 그 ceiling을 적용합니다.

| 옵션 | 동작 |
|------|------|
| `Auto per speaker` (기본) | 파일명 첫 토큰을 화자 ID로 묶고, 4000–8000 Hz를 100 Hz 간격으로 훑은 뒤 20 Hz 간격으로 미세 탐색하여 점수가 최소인 ceiling 사용 |
| `F3–F4 stability` (기준 기본값) | 전체 모음 토큰의 20·log₁₀F3, 20·log₁₀F4 분산 합 최소화. 모음당 1토큰만 있어도 동작 |
| `Within-vowel F1–F2 stability` | 같은 모음 반복 토큰 내 20·log₁₀F1, 20·log₁₀F2 분산(pooled) 합 최소화. 반복 토큰이 없으면 F3–F4 기준으로 자동 대체 |
| `Both combined` | 두 점수의 합 |
| `Optimize per: Speaker` (기본) | 화자당 ceiling 하나 |
| `Optimize per: Speaker × vowel` | 토큰 5개 이상인 모음마다 화자 ceiling의 0.8–1.25배 범위에서 별도 ceiling 탐색 (Escudero et al. 2009) |
| `Fixed 5500 / 5000 / Custom` | 고정 ceiling (기존 방식) |

**3단계 · 모음 토큰 측정**

1. **Praat 분석**: *To Formant (burg)*, 선택된 ceiling, 포먼트 5개, 25 ms 가우시안 창, 10 ms 시간 간격,
   50 Hz부터 pre-emphasis. Burg 방법은 Praat의 표준 LPC 포먼트 추적기입니다.
2. **모음의 어느 지점인가**: 구간의 **가운데 25%**(길이의 37.5%–62.5%)를 씁니다. 모음의 양 끝은 인접 자음의
   영향(coarticulation)을 받고, 중앙이 모음 목표치에 가장 가깝습니다. 20 ms보다 짧은 구간은 중점 한 곳만 측정합니다.
3. **5점 평균**: 그 구간 안의 등간격 5개 시점에서 F1, F2, F3, F4를 읽어(Praat 프레임 사이는 선형 보간) 평균합니다.
   단일 프레임의 추적 튐 현상이 완화됩니다.
4. **범위 검사**: F1과 F2가 모두 100–4000 Hz 안에 있는 토큰만 남깁니다.

**4단계 · 정리와 내보내기**

1. **레이블 정규화**: ARPABET·로마자 레이블을 표시용 IPA로 변환하고(AH → ʌ, eo → ʌ …), 원래 레이블은
   `vowel_raw` 열에 보존합니다.
2. **이상치 제거**: 모음 범주별로 F1 또는 F2가 평균에서 ±3 표준편차를 벗어난 토큰은 그래프 작성 전에 제거합니다.
3. **CSV 다운로드**: 모음 토큰당 한 행이며 열은 `vowel, vowel_raw, F1, F2, F3, F4, time, duration, file, speaker,
   native_language, formant_ceiling`입니다(주파수는 Hz, 소수 첫째 자리 반올림). Bark/ERB/Mel 변환을 선택하면
   그래프의 F1/F2에만 적용됩니다.

**결과**: 모음 구간마다 그 화자의 목소리에 맞춘 ceiling으로 측정한 F1/F2/F3/F4 한 세트가 나옵니다. Auto 모드는
화자당 몇 초가 추가로 걸립니다. 구현: `utils/formant_ceiling.py`, `utils/data_processor.py`.

참고문헌
- Escudero, P., Boersma, P., Rauber, A. S., & Bion, R. A. H. (2009). A cross-dialect acoustic description of vowels: Brazilian and European Portuguese. *JASA*, 126(3), 1379–1393.
- Feinberg, D. R. (2019). Automated Formant Ceiling Settings. OSF Registries. https://doi.org/10.17605/OSF.IO/PDWCB
- Barreda, S. (2021). Fast Track: fast (nearly) automatic formant-tracking using Praat. *Linguistics Vanguard*, 7(1).
- Boersma, P., & Weenink, D. Praat manual, "Sound: To Formant (burg)...". https://www.fon.hum.uva.nl/praat/manual/Sound__To_Formant__burg____.html

### 시각화 유형 선택

- **정적 모음 공간**: F1-F2 평면에서 모음의 분포를 보여줍니다 (모음/화자/언어별 자동 그룹화)
- **타원 모음 공간**: 95% 신뢰 타원으로 각 모음의 클러스터 범위 표시
- **동적 포먼트 궤적**: 시간에 따른 포먼트 변화를 선과 화살표로 표시합니다

### 포먼트 스케일

다양한 심리음향학적 스케일을 지원합니다:

- **Hz (헤르츠)**: 물리적 주파수 (기본값)
- **Bark (바크)**: 임계대역 스케일
- **ERB (등가 직사각 대역폭)**: 청각 필터 기반
- **Mel (멜)**: 음높이 지각 스케일

모든 시각화와 통계 분석은 선택한 스케일에 자동 적용됩니다.

## 📁 프로젝트 구조

```
vowelspace/
├── app.py                          # Flask 메인 애플리케이션
├── requirements.txt                # Python 의존성 패키지
├── README.md                       # 이 파일
├── AUTO_COLUMN_DETECTION_GUIDE.md  # 자동 컬럼 감지 상세 가이드
├── TROUBLESHOOTING.md              # 문제 해결 가이드
├── IMPLEMENTATION_SUMMARY.md       # 기술 구현 요약
├── utils/
│   ├── __init__.py
│   ├── column_detector.py         # 자동 컬럼 감지 로직
│   ├── data_processor.py          # 데이터 처리 유틸리티
│   ├── formant_scales.py          # 포먼트 스케일 변환
│   ├── statistics.py              # 통계 분석 (MANOVA, PCA, LDA 등)
│   └── visualizer.py              # 시각화 함수 (모든 그래프 생성)
├── templates/
│   └── index.html                 # 웹 인터페이스
├── static/
│   └── style.css                  # 스타일시트
├── test/                          # 테스트 데이터 및 예제
└── uploads/                       # 임시 업로드 폴더 (자동 생성)
```

## 🔧 기술 스택

- **Backend**: Flask (Python 3.8+)
- **데이터 처리**: Pandas, NumPy
- **통계 분석**: SciPy, scikit-learn
- **음성 분석**: Parselmouth (Praat Python wrapper)
- **시각화**: Plotly (인터랙티브 그래프)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)

## 📖 API 엔드포인트

### POST `/upload`

파일을 업로드하고 시각화를 생성합니다.

**Parameters:**
- `files`: 업로드할 파일(들)
- `viz_type`: 시각화 유형 (`static`, `dynamic`, `ellipse`)
- `show_ellipses`: 타원 표시 여부 (boolean)
- `show_points`: 개별 데이터 포인트 표시 여부 (boolean)
- `formant_scale`: 포먼트 스케일 (`Hz`, `Bark`, `ERB`, `Mel`)

**Response:**
```json
{
  "success": true,
  "plot": {...},
  "data_summary": {
    "rows": 100,
    "vowels": ["i", "e", "a", "o", "u"],
    "columns": ["vowel", "F1", "F2", "time"],
    "column_detection": {
      "detected": {...},
      "original": {...}
    }
  }
}
```

### POST `/analyze`

통계 분석을 수행합니다.

**Parameters:**
- `files`: 업로드할 파일(들)
- `formant_scale`: 포먼트 스케일

**Response:**
```json
{
  "success": true,
  "analysis": {
    "descriptive": {...},
    "manova": {...},
    "pca": {...},
    "lda": {...},
    "pairwise": {...},
    "vowel_space": {...}
  },
  "plots": {
    "pca": {...},
    "lda_vowel": {...},
    "boxplot_vowel": {...},
    "violin_vowel": {...},
    "histogram_vowel": {...},
    "mean_comparison_vowel": {...},
    "scatter_matrix": {...}
  },
  "column_detection": {...}
}
```

### GET `/example`

예제 데이터로 생성된 시각화를 반환합니다.

## 🎯 예제 데이터

"예제 데이터 보기" 버튼을 클릭하면 5개 모음(i, e, a, o, u)의 샘플 데이터를 볼 수 있습니다.

`test/` 디렉토리에 다음 예제 파일들이 포함되어 있습니다:
- `test_format1.csv` ~ `test_format4.csv`: 다양한 컬럼 형식 예제
- `test_multi_speaker.csv`: 다중 화자 및 언어 데이터
- `*.TextGrid`, `*.wav`: 음성 파일 예제

## 📊 통계 그래프 상세 설명

### 박스플롯 (Box Plot)
- 중앙값, 25-75 백분위수(상자), 최소/최대값(수염), 이상치 표시
- 그룹 간 분포 비교에 유용

### 바이올린 플롯 (Violin Plot)
- 박스플롯 + 확률 밀도 함수
- 분포의 형태를 더 상세하게 표현

### 밀도 플롯 (Density Plot)
- Gaussian KDE로 부드러운 확률 밀도 곡선 생성
- 히스토그램보다 연속적이고 매끄러운 분포 표현
- 여러 그룹의 중첩 비교가 용이

### 평균 비교 플롯 (Mean Comparison)
- 그룹별 평균값과 표준 오차(error bar) 표시
- 샘플 크기(n) 표시
- 그룹 간 차이의 유의성 시각적 확인

### 산점도 행렬 (Scatter Matrix)
- 모든 변수 쌍(F1-F1, F1-F2, F2-F2)의 관계 표시
- **대각선**: 각 포먼트의 분포 (히스토그램)
- **비대각선**: F1 vs F2 산점도 (모음 공간)
- 상관관계 패턴 및 모음 분리도 확인

## ⚙️ 설정

`app.py`에서 다음 설정을 변경할 수 있습니다:

```python
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 최대 파일 크기
app.config['ALLOWED_EXTENSIONS'] = {'wav', 'TextGrid', 'csv', 'txt', 'xlsx', 'xls'}
```

## 🐛 문제 해결

### Parselmouth 설치 오류

일부 시스템에서 Parselmouth 설치가 실패할 수 있습니다:

```bash
# 개발 도구 설치 (Ubuntu/Debian)
sudo apt-get install python3-dev build-essential

# 개발 도구 설치 (macOS)
xcode-select --install

# 재설치 시도
pip install praat-parselmouth
```

### 포트 변경

기본 포트 5000이 사용 중인 경우, `app.py`의 마지막 줄을 수정하세요:

```python
app.run(debug=True, host='0.0.0.0', port=8080)  # 포트를 8080으로 변경
```

## 📝 라이선스

이 프로젝트는 교육 및 연구 목적으로 자유롭게 사용할 수 있습니다.

## 🤝 기여

버그 리포트나 기능 제안은 환영합니다!

## 📧 문의

문제가 발생하거나 질문이 있으면 이슈를 생성해주세요.

## 🔬 연구 활용

이 도구는 다음과 같은 연구에 활용할 수 있습니다:

### 음향 음성학 (Acoustic Phonetics)
- 모음 체계 기술 (vowel inventory description)
- 방언 간 모음 공간 비교
- 음성 변이 연구

### 언어 습득 (Language Acquisition)
- L2 학습자의 모음 공간 vs 원어민 비교
- 연령대별 모음 발달 연구
- 중간언어 분석

### 음성 과학 (Speech Science)
- 화자 정규화 (speaker normalization) 연구
- 성별/연령에 따른 포먼트 차이
- 음성 장애 진단 및 치료 모니터링

### 음성 기술 (Speech Technology)
- TTS/ASR 모델의 정확도 평가
- 음성 합성 품질 검증
- 포먼트 추정 알고리즘 비교

## 📊 인용 (Citation)

이 도구를 연구에 사용하는 경우, 다음과 같이 인용해주세요:

```bibtex
@software{vowelspace2025,
  title = {Vowel Space Visualizer: A Web-Based Tool for Phonetic Analysis},
  author = {{Vowel Space Development Team}},
  year = {2025},
  url = {https://github.com/exphon/vowelspace},
  note = {Version 2.0 with statistical analysis}
}
```

또는:

```
Vowel Space Visualizer (2025). 
A web-based tool for phonetic vowel space visualization and statistical analysis.
https://github.com/exphon/vowelspace
```

## 📚 참고 자료

### 음성학 및 음향 음성학
- [Praat Manual](https://www.fon.hum.uva.nl/praat/manual/Intro.html) - 음성 분석 소프트웨어
- [IPA Chart](https://www.internationalphoneticassociation.org/content/ipa-chart) - 국제 음성 기호

### Python 라이브러리
- [Parselmouth Documentation](https://parselmouth.readthedocs.io/) - Praat Python wrapper
- [Plotly Python Documentation](https://plotly.com/python/) - 인터랙티브 시각화
- [Flask Documentation](https://flask.palletsprojects.com/) - 웹 프레임워크
- [scikit-learn](https://scikit-learn.org/) - 머신러닝 및 통계 분석
- [SciPy](https://scipy.org/) - 과학 계산

### 통계 분석
- [MANOVA Tutorial](https://www.statology.org/manova-python/) - 다변량 분산분석
- [PCA Explained](https://scikit-learn.org/stable/modules/decomposition.html#pca) - 주성분 분석
- [LDA Guide](https://scikit-learn.org/stable/modules/lda_qda.html) - 선형 판별 분석

## 🆕 버전 히스토리

### Version 2.0 (2025-11)
- ✨ 통계 분석 기능 추가 (MANOVA, PCA, LDA)
- 📊 5가지 통계 그래프 추가 (박스플롯, 바이올린, 밀도, 평균비교, 산점도행렬)
- 🔄 포먼트 스케일 변환 지원 (Hz, Bark, ERB, Mel)
- 🎨 타원 모음 공간 시각화
- 🤖 자동 컬럼 감지 개선
- 📈 밀도 플롯 (Gaussian KDE) 구현

### Version 1.0 (2025-01)
- 🎙️ 초기 릴리스
- 정적/동적 모음 공간 시각화
- CSV/WAV/TextGrid 파일 지원
- 자동 컬럼 감지 기본 기능

## 🙏 감사의 글

이 프로젝트는 다음 오픈소스 프로젝트들을 기반으로 합니다:
- [Praat](http://www.praat.org/) by Paul Boersma and David Weenink
- [Parselmouth](https://parselmouth.readthedocs.io/) by Yannick Jadoul
- [Plotly](https://plotly.com/) by Plotly Technologies
- [Flask](https://flask.palletsprojects.com/) by Pallets Team
