"""
Automatic column detection utilities for formant data
Intelligently detects and maps various column naming conventions to standard names
"""
import pandas as pd
import numpy as np
import re


class ColumnDetector:
    """데이터프레임의 컬럼을 자동으로 감지하는 클래스"""
    
    # 컬럼 이름 패턴 정의
    PATTERNS = {
        'F1': [
            r'^f1$', r'^F1$', r'first[\s_-]?formant', r'formant[\s_-]?1',
            r'F1[\s_-]?Hz', r'F1[\s_-]?\(Hz\)', r'f1[\s_-]?frequency',
            r'formant1', r'f1_hz'
        ],
        'F2': [
            r'^f2$', r'^F2$', r'second[\s_-]?formant', r'formant[\s_-]?2',
            r'F2[\s_-]?Hz', r'F2[\s_-]?\(Hz\)', r'f2[\s_-]?frequency',
            r'formant2', r'f2_hz'
        ],
        'F3': [
            r'^f3$', r'^F3$', r'third[\s_-]?formant', r'formant[\s_-]?3',
            r'F3[\s_-]?Hz', r'F3[\s_-]?\(Hz\)', r'f3[\s_-]?frequency',
            r'formant3', r'f3_hz'
        ],
        'vowel': [
            r'^vowel$', r'^phone$', r'^phoneme$', r'^label$', r'^segment$',
            r'vowel[\s_-]?label', r'phone[\s_-]?label', r'^ipa$',
            r'^sound$', r'^v$', r'^vow$', r'^symbol$'
        ],
        'speaker': [
            r'^speaker$', r'^participant$', r'^subject$', r'^informant$',
            r'^talker$', r'speaker[\s_-]?id', r'subject[\s_-]?id',
            r'^spk$', r'^id$', r'^spkr$', r'participant[\s_-]?id'
        ],
        'native_language': [
            r'^native[\s_-]?language$', r'^l1$', r'^first[\s_-]?language$',
            r'^mother[\s_-]?tongue$', r'^language$', r'^lang$',
            r'native[\s_-]?lang', r'L1[\s_-]?language', r'^l1lang$'
        ],
        'time': [
            r'^time$', r'^t$', r'timestamp', r'time[\s_-]?point',
            r'time[\s_-]?\(s\)', r'time[\s_-]?\(ms\)', r'midpoint',
            r'duration[\s_-]?time', r'^sec$', r'^seconds$', r'time_s'
        ],
        'duration': [
            r'^duration$', r'^dur$', r'length', r'duration[\s_-]?\(s\)',
            r'duration[\s_-]?\(ms\)', r'vowel[\s_-]?duration',
            r'segment[\s_-]?duration', r'dur_s', r'dur_ms'
        ],
        'gender': [
            r'^gender$', r'^sex$', r'^m/f$', r'speaker[\s_-]?gender',
            r'participant[\s_-]?gender', r'^g$'
        ],
        'age': [
            r'^age$', r'speaker[\s_-]?age', r'participant[\s_-]?age',
            r'age[\s_-]?\(years\)', r'^yrs$'
        ]
    }
    
    @staticmethod
    def detect_columns(df):
        """
        데이터프레임의 컬럼을 자동으로 감지
        
        Returns:
            dict: {표준컬럼명: 실제컬럼명}
        """
        detected = {}
        columns_lower = {col: col.lower().strip() for col in df.columns}
        used_columns = set()  # 이미 매핑된 컬럼 추적
        
        # 1단계: 패턴 매칭
        for standard_name, patterns in ColumnDetector.PATTERNS.items():
            for col, col_lower in columns_lower.items():
                if col in used_columns:
                    continue
                    
                # 패턴 매칭
                for pattern in patterns:
                    if re.match(pattern, col_lower, re.IGNORECASE):
                        detected[standard_name] = col
                        used_columns.add(col)
                        break
                
                if standard_name in detected:
                    break
        
        # 2단계: 패턴으로 찾지 못한 경우 휴리스틱 사용
        if 'F1' not in detected:
            f1_col = ColumnDetector._find_formant_by_value(df, 1, used_columns)
            if f1_col:
                detected['F1'] = f1_col
                used_columns.add(f1_col)
        
        if 'F2' not in detected:
            f2_col = ColumnDetector._find_formant_by_value(df, 2, used_columns)
            if f2_col:
                detected['F2'] = f2_col
                used_columns.add(f2_col)
        
        if 'F3' not in detected:
            f3_col = ColumnDetector._find_formant_by_value(df, 3, used_columns)
            if f3_col:
                detected['F3'] = f3_col
                used_columns.add(f3_col)
        
        # time 컬럼 휴리스틱 검사
        if 'time' not in detected:
            time_col = ColumnDetector._find_time_column(df, used_columns)
            if time_col:
                detected['time'] = time_col
                used_columns.add(time_col)
        
        # vowel 컬럼 휴리스틱 검사
        if 'vowel' not in detected:
            vowel_col = ColumnDetector._find_vowel_column(df, used_columns)
            if vowel_col:
                detected['vowel'] = vowel_col
                used_columns.add(vowel_col)
        
        # speaker 컬럼 휴리스틱 검사
        if 'speaker' not in detected:
            speaker_col = ColumnDetector._find_categorical_column(df, max_unique=50, used_columns=used_columns)
            if speaker_col:
                detected['speaker'] = speaker_col
                used_columns.add(speaker_col)
        
        return detected
    
    @staticmethod
    def _find_formant_by_value(df, formant_num, used_columns):
        """값의 범위로 포먼트 컬럼 찾기"""
        # F1: 200-1000 Hz, F2: 800-3000 Hz, F3: 1500-4000 Hz
        ranges = {
            1: (200, 1000),
            2: (800, 3000),
            3: (1500, 4000)
        }
        
        min_val, max_val = ranges.get(formant_num, (0, 10000))
        
        for col in df.columns:
            if col in used_columns:
                continue
                
            if pd.api.types.is_numeric_dtype(df[col]):
                # NaN이 아닌 값들만 사용
                non_null_values = df[col].dropna()
                if len(non_null_values) == 0:
                    continue
                
                col_min = non_null_values.min()
                col_max = non_null_values.max()
                col_mean = non_null_values.mean()
                
                # 값의 범위가 포먼트 범위와 일치하는지 확인
                if min_val <= col_mean <= max_val:
                    if col_min >= min_val * 0.5 and col_max <= max_val * 1.5:
                        return col
        
        return None
    
    @staticmethod
    def _find_time_column(df, used_columns):
        """시간 컬럼 찾기 (숫자이고 순차적으로 증가)"""
        for col in df.columns:
            if col in used_columns:
                continue
                
            if pd.api.types.is_numeric_dtype(df[col]):
                non_null_values = df[col].dropna()
                if len(non_null_values) == 0:
                    continue
                
                # 값이 0 이상이고 작은 값 (보통 초 단위)
                if non_null_values.min() >= 0 and non_null_values.max() < 10000:
                    # 값이 순차적으로 증가하는지 확인 (대부분이 양수 차이)
                    diffs = df[col].diff().dropna()
                    if len(diffs) > 0:
                        positive_ratio = (diffs >= 0).sum() / len(diffs)
                        if positive_ratio > 0.8:  # 80% 이상이 증가
                            return col
        
        return None
    
    @staticmethod
    def _find_vowel_column(df, used_columns):
        """모음 컬럼 찾기 (문자열이고 짧은 값)"""
        for col in df.columns:
            if col in used_columns:
                continue
                
            if df[col].dtype == 'object' or pd.api.types.is_string_dtype(df[col]):
                # 고유값 개수가 적고 (보통 모음은 5-30개)
                unique_count = df[col].nunique()
                if 2 <= unique_count <= 30:
                    # 대부분의 값이 1-5글자
                    non_null = df[col].dropna()
                    if len(non_null) == 0:
                        continue
                    
                    avg_length = non_null.astype(str).str.len().mean()
                    if avg_length <= 8:
                        # IPA 모음 기호 포함 여부 확인
                        sample_values = non_null.unique()[:10]
                        vowel_chars = set('iɪeɛæaɑɒʌɔoʊuɯʏyøœɜəɘɵɤɐ')
                        
                        for val in sample_values:
                            if any(char in vowel_chars for char in str(val).lower()):
                                return col
                        
                        # 영어 모음 표기도 확인
                        english_vowels = {'i', 'e', 'a', 'o', 'u', 'ih', 'eh', 'ae', 'ah', 'ao', 'uh', 'uw', 'iy', 'ey', 'ay', 'oy', 'aw', 'ow'}
                        if any(str(val).lower() in english_vowels for val in sample_values):
                            return col
        
        return None
    
    @staticmethod
    def _find_categorical_column(df, max_unique=50, used_columns=set()):
        """카테고리형 컬럼 찾기 (화자, 언어 등)"""
        for col in df.columns:
            if col in used_columns:
                continue
                
            if df[col].dtype == 'object' or pd.api.types.is_string_dtype(df[col]):
                unique_count = df[col].nunique()
                if 2 <= unique_count <= max_unique:
                    return col
        
        return None
    
    @staticmethod
    def rename_columns(df, column_mapping):
        """
        감지된 컬럼 매핑을 사용하여 컬럼 이름 변경
        
        Args:
            df: 원본 데이터프레임
            column_mapping: {표준명: 실제컬럼명}
        
        Returns:
            새로운 컬럼명이 적용된 데이터프레임 복사본
        """
        # 역매핑 생성 (실제컬럼명 -> 표준명)
        reverse_mapping = {v: k for k, v in column_mapping.items()}
        
        df_renamed = df.rename(columns=reverse_mapping)
        return df_renamed
    
    @staticmethod
    def validate_required_columns(detected_columns):
        """필수 컬럼이 감지되었는지 확인"""
        required = ['F1', 'F2']
        missing = [col for col in required if col not in detected_columns]
        
        if missing:
            raise ValueError(f"필수 컬럼을 찾을 수 없습니다: {', '.join(missing)}. "
                           f"F1과 F2 열이 있는지 확인하거나, 200-1000 Hz (F1) 및 800-3000 Hz (F2) 범위의 숫자 열이 있는지 확인하세요.")
        
        return True
    
    @staticmethod
    def get_column_info(df, detected_columns):
        """감지된 컬럼에 대한 정보 반환"""
        info = {
            'detected': detected_columns,
            'details': {}
        }
        
        for standard_name, actual_name in detected_columns.items():
            col_data = df[actual_name]
            
            info['details'][standard_name] = {
                'actual_name': actual_name,
                'dtype': str(col_data.dtype),
                'non_null_count': int(col_data.notna().sum()),
                'null_count': int(col_data.isna().sum()),
            }
            
            if pd.api.types.is_numeric_dtype(col_data):
                non_null = col_data.dropna()
                if len(non_null) > 0:
                    info['details'][standard_name].update({
                        'min': float(non_null.min()),
                        'max': float(non_null.max()),
                        'mean': float(non_null.mean()),
                        'std': float(non_null.std()) if len(non_null) > 1 else 0.0
                    })
            else:
                unique_vals = col_data.dropna().unique()
                info['details'][standard_name].update({
                    'unique_count': int(col_data.nunique()),
                    'sample_values': [str(v) for v in unique_vals[:5]]
                })
        
        return info


def auto_detect_and_rename(df):
    """
    데이터프레임의 컬럼을 자동 감지하고 표준 이름으로 변경
    
    Returns:
        tuple: (변경된 df, 감지 정보)
    """
    detector = ColumnDetector()
    
    # 컬럼 감지
    detected = detector.detect_columns(df)
    
    # 필수 컬럼 검증
    detector.validate_required_columns(detected)
    
    # 정보 수집 (이름 변경 전에)
    info = detector.get_column_info(df, detected)
    
    # 컬럼명 변경
    df_renamed = detector.rename_columns(df, detected)
    
    return df_renamed, info
