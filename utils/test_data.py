"""
Test data generation for multi-speaker vowel space analysis
"""
import pandas as pd
import numpy as np


def generate_test_data():
    """여러 화자 및 모국어별 테스트 데이터 생성"""
    
    # 모음별 기준 포먼트 값 (Hz)
    vowel_prototypes = {
        'i': {'F1': 300, 'F2': 2300},
        'e': {'F1': 450, 'F2': 2100},
        'a': {'F1': 700, 'F2': 1200},
        'o': {'F1': 450, 'F2': 900},
        'u': {'F1': 300, 'F2': 800},
    }
    
    # 화자 정보 (이름, 모국어, F1 shift, F2 shift)
    speakers = [
        ('Speaker_A', 'Korean', 0, 0),
        ('Speaker_B', 'Korean', 30, 50),
        ('Speaker_C', 'English', -20, 100),
        ('Speaker_D', 'English', 20, -80),
        ('Speaker_E', 'Japanese', 10, 150),
        ('Speaker_F', 'Japanese', -10, -100),
    ]
    
    data = []
    
    for speaker_name, native_lang, f1_shift, f2_shift in speakers:
        for vowel, formants in vowel_prototypes.items():
            # 각 모음당 10개 데이터 포인트 생성 (시간에 따른 변화)
            for i in range(10):
                time = i * 0.05  # 0.05초 간격
                
                # 약간의 무작위 변동 추가
                f1 = formants['F1'] + f1_shift + np.random.normal(0, 20)
                f2 = formants['F2'] + f2_shift + np.random.normal(0, 50)
                
                # 시간에 따른 약간의 변화
                f1 += np.sin(time * 2 * np.pi) * 10
                f2 += np.cos(time * 2 * np.pi) * 30
                
                data.append({
                    'speaker': speaker_name,
                    'native_language': native_lang,
                    'vowel': vowel,
                    'F1': max(200, f1),  # 최소값 제한
                    'F2': max(500, f2),
                    'time': time,
                    'duration': 0.5
                })
    
    return pd.DataFrame(data)


def save_test_data_to_csv(filename='test_multi_speaker.csv'):
    """테스트 데이터를 CSV 파일로 저장"""
    df = generate_test_data()
    df.to_csv(filename, index=False)
    print(f"Test data saved to {filename}")
    print(f"Total rows: {len(df)}")
    print(f"Speakers: {df['speaker'].unique()}")
    print(f"Native Languages: {df['native_language'].unique()}")
    print(f"Vowels: {df['vowel'].unique()}")
    return df


def generate_varied_column_names_data():
    """다양한 컬럼명 형식으로 테스트 데이터 생성 (자동 감지 테스트용)"""
    
    test_formats = [
        # Format 1: 일반적인 형식
        {
            'filename': 'test_format1.csv',
            'columns': {'speaker': 'speaker', 'native_language': 'L1', 'vowel': 'vowel', 'F1': 'F1', 'F2': 'F2', 'time': 'time', 'duration': 'duration'}
        },
        # Format 2: 소문자 + 언더스코어
        {
            'filename': 'test_format2.csv',
            'columns': {'speaker': 'participant', 'native_language': 'native_lang', 'vowel': 'phone', 'F1': 'f1_frequency', 'F2': 'f2_frequency', 'time': 'time_s', 'duration': 'dur'}
        },
        # Format 3: 상세한 이름
        {
            'filename': 'test_format3.csv',
            'columns': {'speaker': 'subject_id', 'native_language': 'mother_tongue', 'vowel': 'phoneme', 'F1': 'first_formant', 'F2': 'second_formant', 'time': 'timestamp', 'duration': 'length'}
        },
        # Format 4: 약어
        {
            'filename': 'test_format4.csv',
            'columns': {'speaker': 'spk', 'native_language': 'lang', 'vowel': 'v', 'F1': 'f1', 'F2': 'f2', 'time': 't', 'duration': 'dur_s'}
        },
    ]
    
    base_df = generate_test_data()
    
    saved_files = []
    for fmt in test_formats:
        # 컬럼명 변경
        df_renamed = base_df.rename(columns=fmt['columns'])
        
        # 파일 저장
        filepath = f"/var/www/html/vowelspace/test/{fmt['filename']}"
        df_renamed.to_csv(filepath, index=False)
        print(f"Created {filepath} with columns: {list(df_renamed.columns)}")
        saved_files.append(filepath)
    
    return saved_files


if __name__ == '__main__':
    import os
    
    # 테스트 디렉토리 생성
    os.makedirs('/var/www/html/vowelspace/test', exist_ok=True)
    
    # 기본 테스트 데이터 생성
    print("=== Generating basic test data ===")
    save_test_data_to_csv('/var/www/html/vowelspace/test/test_multi_speaker.csv')
    
    print("\n=== Generating varied column format data ===")
    generate_varied_column_names_data()
    
    print("\nAll test data generated successfully!")
