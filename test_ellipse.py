#!/usr/bin/env python3
"""
타원 시각화 테스트
"""
import requests
import json

BASE_URL = 'http://localhost:5000'
TEST_FILE = '/var/www/html/vowelspace/test/test_multi_speaker.csv'

print("=== 타원 시각화 테스트 ===\n")

# 1. Static 시각화 테스트
print("1. 일반 정적 시각화...")
with open(TEST_FILE, 'rb') as f:
    files = {'files': ('test_multi_speaker.csv', f, 'text/csv')}
    data = {'viz_type': 'static'}
    response = requests.post(f'{BASE_URL}/upload', files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("  ✅ 성공: 일반 정적 시각화")
        else:
            print(f"  ❌ 실패: {result.get('error')}")
    else:
        print(f"  ❌ HTTP 오류: {response.status_code}")

# 2. 타원 시각화 (포인트 포함) 테스트
print("\n2. 타원 시각화 (포인트 포함)...")
with open(TEST_FILE, 'rb') as f:
    files = {'files': ('test_multi_speaker.csv', f, 'text/csv')}
    data = {
        'viz_type': 'ellipse',
        'show_ellipses': 'true',
        'show_points': 'true'
    }
    response = requests.post(f'{BASE_URL}/upload', files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("  ✅ 성공: 타원 + 포인트")
            summary = result.get('data_summary', {})
            print(f"     - 데이터 포인트: {summary.get('rows')}")
            print(f"     - 모음: {', '.join(summary.get('vowels', []))}")
        else:
            print(f"  ❌ 실패: {result.get('error')}")
    else:
        print(f"  ❌ HTTP 오류: {response.status_code}")

# 3. 타원만 시각화 테스트
print("\n3. 타원만 시각화 (포인트 제외)...")
with open(TEST_FILE, 'rb') as f:
    files = {'files': ('test_multi_speaker.csv', f, 'text/csv')}
    data = {
        'viz_type': 'ellipse',
        'show_ellipses': 'true',
        'show_points': 'false'
    }
    response = requests.post(f'{BASE_URL}/upload', files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("  ✅ 성공: 타원만 (포인트 제외)")
        else:
            print(f"  ❌ 실패: {result.get('error')}")
    else:
        print(f"  ❌ HTTP 오류: {response.status_code}")

# 4. 동적 궤적 시각화 테스트
print("\n4. 동적 포먼트 궤적...")
with open(TEST_FILE, 'rb') as f:
    files = {'files': ('test_multi_speaker.csv', f, 'text/csv')}
    data = {'viz_type': 'dynamic'}
    response = requests.post(f'{BASE_URL}/upload', files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("  ✅ 성공: 동적 궤적")
        else:
            print(f"  ❌ 실패: {result.get('error')}")
    else:
        print(f"  ❌ HTTP 오류: {response.status_code}")

print("\n=== 테스트 완료 ===")
print("\n💡 웹 브라우저에서 확인:")
print(f"   {BASE_URL}")
print("\n✨ 새로운 기능:")
print("   1. 시각화 유형에서 '타원 모음 공간' 선택")
print("   2. 각 모음/화자/언어별로 95% 신뢰 타원 표시")
print("   3. 개별 데이터 포인트 표시 옵션")
print("   4. 레전드 클릭으로 특정 그룹 선택 가능")
