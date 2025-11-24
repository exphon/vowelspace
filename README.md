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

Python 3.8 이상이 필요합니다.

```bash
# 가상 환경 생성 (선택사항이지만 권장)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

### 2. 의존성 패키지 설치

```bash
cd /var/www/html/vowelspace
pip install -r requirements.txt
```

### 3. 애플리케이션 실행

```bash
python app.py
```

브라우저에서 `http://localhost:5000` 을 열면 애플리케이션을 사용할 수 있습니다.

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

1. **WAV만**: 자동으로 포먼트를 추출합니다
2. **WAV + TextGrid**: TextGrid의 레이블된 구간에서 포먼트를 추출합니다

TextGrid 파일은 Praat 형식이어야 하며, 모음 레이블이 포함된 interval tier가 있어야 합니다.

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
