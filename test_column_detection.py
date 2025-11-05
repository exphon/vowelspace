"""
Test script for automatic column detection
"""
import sys
import pandas as pd
from utils.column_detector import auto_detect_and_rename, ColumnDetector

def test_column_detection(filepath):
    """테스트 파일의 컬럼 감지 테스트"""
    print(f"\n{'='*60}")
    print(f"Testing: {filepath}")
    print(f"{'='*60}")
    
    # 파일 읽기
    df = pd.read_csv(filepath)
    print(f"\n원본 컬럼: {list(df.columns)}")
    print(f"데이터 행 수: {len(df)}")
    
    # 자동 감지
    try:
        df_renamed, info = auto_detect_and_rename(df)
        
        print(f"\n✅ 감지 성공!")
        print(f"\n감지된 컬럼 매핑:")
        for standard, actual in info['detected'].items():
            print(f"  {standard:20} <- {actual}")
        
        print(f"\n상세 정보:")
        for standard, details in info['details'].items():
            print(f"\n  [{standard}]")
            print(f"    실제 컬럼명: {details['actual_name']}")
            print(f"    데이터 타입: {details['dtype']}")
            print(f"    유효 데이터: {details['non_null_count']} / {details['non_null_count'] + details['null_count']}")
            
            if 'min' in details:
                print(f"    범위: {details['min']:.1f} - {details['max']:.1f}")
                print(f"    평균: {details['mean']:.1f} ± {details['std']:.1f}")
            elif 'unique_count' in details:
                print(f"    고유값: {details['unique_count']}개")
                print(f"    샘플: {', '.join(details['sample_values'][:5])}")
        
        print(f"\n변환 후 컬럼: {list(df_renamed.columns)}")
        
        # 샘플 데이터 출력
        print(f"\n첫 5행 (변환 후):")
        print(df_renamed.head().to_string())
        
        return True
        
    except Exception as e:
        print(f"\n❌ 감지 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    test_files = [
        '/var/www/html/vowelspace/test/test_format1.csv',
        '/var/www/html/vowelspace/test/test_format2.csv',
        '/var/www/html/vowelspace/test/test_format3.csv',
        '/var/www/html/vowelspace/test/test_format4.csv',
        '/var/www/html/vowelspace/test/test_multi_speaker.csv',
    ]
    
    print("자동 컬럼 감지 테스트 시작")
    print("="*60)
    
    results = {}
    for filepath in test_files:
        try:
            results[filepath] = test_column_detection(filepath)
        except FileNotFoundError:
            print(f"\n❌ 파일을 찾을 수 없음: {filepath}")
            results[filepath] = False
        except Exception as e:
            print(f"\n❌ 예외 발생: {e}")
            results[filepath] = False
    
    # 결과 요약
    print(f"\n{'='*60}")
    print("테스트 결과 요약")
    print(f"{'='*60}")
    
    for filepath, success in results.items():
        filename = filepath.split('/')[-1]
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{status}: {filename}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\n총 {total}개 중 {passed}개 성공 ({passed/total*100:.1f}%)")
