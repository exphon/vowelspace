"""
간단한 웹 테스트 스크립트 - 자동 컬럼 감지 확인
"""
import requests
import json

BASE_URL = 'http://localhost:5000'

def test_upload_with_auto_detection():
    """다양한 컬럼명 형식의 파일 업로드 테스트"""
    
    test_files = [
        ('test_format2.csv', 'Format 2: f1_frequency, f2_frequency, phone, participant'),
        ('test_format3.csv', 'Format 3: first_formant, second_formant, phoneme, subject_id'),
        ('test_format4.csv', 'Format 4: f1, f2, v, spk'),
    ]
    
    for filename, description in test_files:
        print(f"\n{'='*70}")
        print(f"테스트: {description}")
        print(f"파일: {filename}")
        print(f"{'='*70}")
        
        filepath = f'/var/www/app/vowelspace/test/{filename}'
        
        try:
            with open(filepath, 'rb') as f:
                files = {'files': (filename, f, 'text/csv')}
                data = {'viz_type': 'static'}
                
                response = requests.post(f'{BASE_URL}/upload', files=files, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('success'):
                        print("✅ 업로드 및 처리 성공!")
                        
                        # 데이터 요약 출력
                        summary = result.get('data_summary', {})
                        print(f"\n데이터 요약:")
                        print(f"  - 총 행: {summary.get('rows', 0)}")
                        print(f"  - 모음: {', '.join(summary.get('vowels', []))}")
                        print(f"  - 컬럼: {', '.join(summary.get('columns', []))}")
                        
                        # 컬럼 감지 정보 출력
                        col_detection = summary.get('column_detection')
                        if col_detection and col_detection.get('details'):
                            print(f"\n자동 감지된 컬럼:")
                            for std_name, info in col_detection['details'].items():
                                actual = info['actual_name']
                                print(f"  - {std_name:20} <- {actual}")
                                
                                if 'min' in info:
                                    print(f"    범위: {info['min']:.0f} - {info['max']:.0f} Hz")
                                elif 'unique_count' in info:
                                    print(f"    고유값: {info['unique_count']}개")
                        
                        print("\n✨ 시각화 생성 완료!")
                    else:
                        print(f"❌ 처리 실패: {result.get('error', '알 수 없는 오류')}")
                else:
                    print(f"❌ HTTP 오류: {response.status_code}")
                    print(f"응답: {response.text[:200]}")
        
        except FileNotFoundError:
            print(f"❌ 파일을 찾을 수 없음: {filepath}")
        except Exception as e:
            print(f"❌ 예외 발생: {e}")
            import traceback
            traceback.print_exc()


def test_example_endpoint():
    """예제 데이터 엔드포인트 테스트"""
    print(f"\n{'='*70}")
    print("예제 데이터 테스트")
    print(f"{'='*70}")
    
    try:
        response = requests.get(f'{BASE_URL}/example')
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ 예제 데이터 생성 성공!")
                print("✨ 시각화 확인: http://localhost:5000")
            else:
                print(f"❌ 실패: {result.get('error')}")
        else:
            print(f"❌ HTTP 오류: {response.status_code}")
    
    except Exception as e:
        print(f"❌ 예외 발생: {e}")


if __name__ == '__main__':
    print("🧪 Vowel Space Visualizer - 자동 컬럼 감지 테스트")
    print("="*70)
    
    # 서버 연결 확인
    try:
        response = requests.get(BASE_URL, timeout=2)
        print("✅ 서버 연결 확인")
    except:
        print("❌ 서버가 실행 중이지 않습니다. 먼저 app.py를 실행하세요.")
        exit(1)
    
    # 테스트 실행
    test_upload_with_auto_detection()
    test_example_endpoint()
    
    print(f"\n{'='*70}")
    print("테스트 완료!")
    print("웹 브라우저에서 http://localhost:5000 을 열어 확인하세요.")
    print(f"{'='*70}")
