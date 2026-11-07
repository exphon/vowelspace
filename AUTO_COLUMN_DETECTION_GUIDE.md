# 자동 컬럼 감지 기능 사용 가이드

## 🎯 개요

Vowel Space Visualizer는 이제 **지능형 자동 컬럼 감지** 기능을 지원합니다! 
다양한 형식의 데이터 파일을 업로드하면 시스템이 자동으로 필요한 컬럼을 찾아서 처리합니다.

## ✨ 주요 기능

### 1. 다양한 컬럼명 자동 인식

더 이상 컬럼 이름을 정확히 맞출 필요가 없습니다! 다음과 같은 다양한 이름을 자동으로 인식합니다:

| 용도 | 인식되는 컬럼명 예시 |
|------|---------------------|
| **F1 포먼트** | `f1`, `F1`, `first_formant`, `formant_1`, `F1_Hz`, `f1_frequency` |
| **F2 포먼트** | `f2`, `F2`, `second_formant`, `formant_2`, `F2_Hz`, `f2_frequency` |
| **모음** | `vowel`, `phone`, `phoneme`, `label`, `segment`, `ipa`, `v` |
| **화자** | `speaker`, `participant`, `subject`, `informant`, `spk`, `id` |
| **모국어** | `native_language`, `L1`, `first_language`, `lang` |
| **시간** | `time`, `t`, `timestamp`, `time_point`, `sec` |

### 2. 값 범위 기반 자동 감지

컬럼 이름이 표준과 다르더라도 **값의 범위**를 분석하여 자동으로 감지합니다:

- **F1**: 200-1000 Hz 범위의 숫자 → 자동으로 F1로 인식
- **F2**: 800-3000 Hz 범위의 숫자 → 자동으로 F2로 인식
- **모음**: 1-5글자의 짧은 문자열 → 자동으로 모음 레이블로 인식

## 📋 사용 예시

### 예시 1: 연구실 A의 데이터

```csv
phoneme,first_formant,second_formant,participant,L1
i,300,2300,Subject_01,Korean
e,450,2100,Subject_01,Korean
```

✅ **자동 감지 결과:**
- `phoneme` → `vowel`
- `first_formant` → `F1`
- `second_formant` → `F2`
- `participant` → `speaker`
- `L1` → `native_language`

### 예시 2: 연구실 B의 데이터

```csv
v,f1_frequency,f2_frequency,spk,lang
i,300,2300,SP01,Korean
e,450,2100,SP01,Korean
```

✅ **자동 감지 결과:**
- `v` → `vowel`
- `f1_frequency` → `F1`
- `f2_frequency` → `F2`
- `spk` → `speaker`
- `lang` → `native_language`

### 예시 3: 컬럼명이 없는 숫자 데이터

```csv
vowel,300,2300
vowel2,450,2100
```

✅ **자동 감지 결과:**
- 시스템이 값의 범위(300은 F1, 2300은 F2)를 분석하여 자동으로 포먼트 컬럼 감지

## 🔍 감지 결과 확인

파일 업로드 후 **"데이터 요약"** 섹션에서 다음 정보를 확인할 수 있습니다:

```
자동 감지된 컬럼:
  - F1: "first_formant" (범위: 250-850 Hz, 평균: 450 Hz)
  - F2: "second_formant" (범위: 800-2500 Hz, 평균: 1650 Hz)
  - vowel: "phone" (고유값 5개) [예: i, e, a, o, u]
  - speaker: "participant" (고유값 3개) [예: SP01, SP02, SP03]
  - native_language: "L1" (고유값 2개) [예: Korean, English]
```

## 📊 테스트 데이터

프로젝트에는 다양한 형식의 테스트 데이터가 포함되어 있습니다:

```bash
/var/www/app/vowelspace/test/
  ├── test_format1.csv    # 표준 형식 (F1, F2, vowel, speaker, L1)
  ├── test_format2.csv    # 상세 형식 (f1_frequency, phone, participant)
  ├── test_format3.csv    # 학술 형식 (first_formant, phoneme, subject_id)
  ├── test_format4.csv    # 약어 형식 (f1, f2, v, spk)
  └── test_multi_speaker.csv  # 다중 화자 데이터
```

테스트 방법:
```bash
cd /var/www/app/vowelspace
python3 test_column_detection.py  # 컬럼 감지 테스트
python3 test_web_upload.py        # 웹 업로드 테스트
```

## 🚀 사용 방법

1. **웹 인터페이스에서:**
   - http://localhost:5000 접속
   - 파일 업로드 (어떤 컬럼명이든 OK!)
   - 자동으로 감지된 컬럼 확인
   - 시각화 결과 확인

2. **Python 코드에서:**
   ```python
   from utils.data_processor import process_csv_xlsx
   
   # auto_detect=True (기본값)
   df, detection_info = process_csv_xlsx('your_data.csv', auto_detect=True)
   
   print(detection_info['detected'])  # 감지된 컬럼 매핑
   print(df.head())  # 표준화된 데이터
   ```

## ⚙️ 고급 기능

### 직접 컬럼 감지 사용

```python
from utils.column_detector import auto_detect_and_rename
import pandas as pd

# 데이터 로드
df = pd.read_csv('your_data.csv')

# 자동 감지 및 이름 변경
df_standardized, info = auto_detect_and_rename(df)

# 감지 정보 확인
print("감지된 컬럼:", info['detected'])
print("상세 정보:", info['details'])
```

### 커스텀 패턴 추가

`utils/column_detector.py`의 `PATTERNS` 딕셔너리를 수정하여 
추가 패턴을 인식할 수 있습니다:

```python
PATTERNS = {
    'F1': [
        r'^f1$', r'^F1$', 
        r'your_custom_pattern',  # 여기에 추가
    ],
    # ...
}
```

## 💡 팁

1. **필수 컬럼**: F1과 F2는 반드시 감지되어야 합니다 (없으면 오류)
2. **선택 컬럼**: vowel, speaker, time 등은 선택사항
3. **우선순위**: 패턴 매칭 → 값 범위 분석 → 휴리스틱 분석 순으로 진행
4. **중복 방지**: 한 컬럼은 하나의 표준명에만 매핑됨

## 🐛 문제 해결

### Q: 컬럼이 잘못 감지되었어요
**A:** 컬럼명을 더 명확하게 변경하거나, 값의 범위를 확인하세요.

### Q: F1/F2가 감지되지 않아요
**A:** 
- 값이 적절한 범위(F1: 200-1000 Hz, F2: 800-3000 Hz)에 있는지 확인
- 컬럼명에 'f1', 'F1', 'formant' 등의 키워드 포함 여부 확인

### Q: 여러 컬럼이 같은 표준명으로 매핑되어요
**A:** 시스템은 첫 번째로 매칭된 컬럼만 사용합니다. 중복 컬럼명 제거 필요.

## 📚 추가 자료

- [README.md](README.md) - 전체 프로젝트 문서
- [utils/column_detector.py](utils/column_detector.py) - 감지 알고리즘 소스코드
- [test_column_detection.py](test_column_detection.py) - 테스트 스크립트

---

**Vowel Space Visualizer** - 이제 데이터 형식 걱정 없이 연구에 집중하세요! 🎵
