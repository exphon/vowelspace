# 🎙️ Vowel Space Visualizer

음성학 연구를 위한 모음 공간 및 포먼트 궤적 시각화 웹 애플리케이션입니다.

## � 빠른 링크

- [자동 컬럼 감지 가이드](AUTO_COLUMN_DETECTION_GUIDE.md) - 다양한 데이터 형식 자동 인식 기능
- [문제 해결 가이드](TROUBLESHOOTING.md) - 일반적인 문제 해결 방법

## �📋 기능

- **정적 모음 공간 시각화**: F1과 F2 값을 기반으로 전통적인 모음 공간 플롯 생성
- **동적 포먼트 궤적 시각화**: 시간에 따른 포먼트 변화를 추적하고 시각화
- **🤖 자동 컬럼 감지**: 다양한 형식의 컬럼명을 지능적으로 인식하고 표준화 ([상세 가이드](AUTO_COLUMN_DETECTION_GUIDE.md))
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

### CSV/TXT/XLSX 파일 업로드

파일에 다음 열이 포함되어야 합니다:

**필수 열:**
- `F1`: 첫 번째 포먼트 주파수 (Hz)
- `F2`: 두 번째 포먼트 주파수 (Hz)

**선택 열:**
- `vowel`: 모음 레이블 (예: i, e, a, o, u)
- `time`: 시간 정보 (초 단위, 동적 시각화용)
- `duration`: 지속 시간 (초 단위)

**예시 CSV:**
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

- **정적 모음 공간**: F1-F2 평면에서 모음의 분포를 보여줍니다
- **동적 포먼트 궤적**: 시간에 따른 포먼트 변화를 선과 화살표로 표시합니다

## 📁 프로젝트 구조

```
vowelspace/
├── app.py                  # Flask 메인 애플리케이션
├── requirements.txt        # Python 의존성 패키지
├── utils/
│   ├── data_processor.py  # 데이터 처리 유틸리티
│   └── visualizer.py      # 시각화 함수
├── templates/
│   └── index.html         # 웹 인터페이스
├── static/
│   └── style.css          # 스타일시트
└── uploads/               # 임시 업로드 폴더 (자동 생성)
```

## 🔧 기술 스택

- **Backend**: Flask (Python)
- **데이터 처리**: Pandas, NumPy
- **음성 분석**: Parselmouth (Praat Python wrapper)
- **시각화**: Plotly
- **Frontend**: HTML, CSS, JavaScript

## 📖 API 엔드포인트

### POST `/upload`

파일을 업로드하고 시각화를 생성합니다.

**Parameters:**
- `files`: 업로드할 파일(들)
- `viz_type`: 시각화 유형 (`static` 또는 `dynamic`)

**Response:**
```json
{
  "success": true,
  "plot": {...},
  "data_summary": {
    "rows": 100,
    "vowels": ["i", "e", "a", "o", "u"],
    "columns": ["vowel", "F1", "F2", "time"]
  }
}
```

### GET `/example`

예제 데이터로 생성된 시각화를 반환합니다.

## 🎯 예제 데이터

"예제 데이터 보기" 버튼을 클릭하면 5개 모음(i, e, a, o, u)의 샘플 데이터를 볼 수 있습니다.

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

이 도구를 연구에 사용하는 경우, 다음과 같이 인용해주세요:

```
Vowel Space Visualizer (2025). 
A web-based tool for phonetic vowel space and formant trajectory visualization.
```

## 📚 참고 자료

- [Praat Manual](https://www.fon.hum.uva.nl/praat/manual/Intro.html)
- [Parselmouth Documentation](https://parselmouth.readthedocs.io/)
- [Plotly Python Documentation](https://plotly.com/python/)
- [Flask Documentation](https://flask.palletsprojects.com/)
