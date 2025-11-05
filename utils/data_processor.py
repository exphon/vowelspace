"""
Data processing utilities for handling CSV, XLSX, WAV, and TextGrid files
"""
import pandas as pd
import numpy as np
try:
    import parselmouth
    from parselmouth.praat import call
except ImportError:
    parselmouth = None

from .column_detector import auto_detect_and_rename, ColumnDetector


def process_csv_xlsx(filepath, auto_detect=True):
    """
    Process CSV, TXT, or XLSX files containing formant data
    Expected columns: vowel, F1, F2, (optional: F3, time, duration)
    TXT files should be tab-separated or comma-separated
    
    Args:
        filepath: Path to the file
        auto_detect: If True, automatically detect and rename columns
    
    Returns:
        DataFrame with standardized column names, or tuple (DataFrame, detection_info) if auto_detect=True
    """
    try:
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        elif filepath.endswith('.txt'):
            # Try to detect separator (tab or comma)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    if '\t' in first_line:
                        df = pd.read_csv(filepath, sep='\t', encoding='utf-8')
                    else:
                        df = pd.read_csv(filepath, sep=',', encoding='utf-8')
            except UnicodeDecodeError:
                # Try different encoding
                with open(filepath, 'r', encoding='latin-1') as f:
                    first_line = f.readline()
                    if '\t' in first_line:
                        df = pd.read_csv(filepath, sep='\t', encoding='latin-1')
                    else:
                        df = pd.read_csv(filepath, sep=',', encoding='latin-1')
        else:
            df = pd.read_excel(filepath)
        
        detection_info = None
        
        if auto_detect:
            # 자동 컬럼 감지 및 이름 변경
            df, detection_info = auto_detect_and_rename(df)
            print(f"Auto-detected columns: {detection_info['detected']}")
        else:
            # 기존 방식: 소문자로 정규화
            df.columns = df.columns.str.lower().str.strip()
            
            # Check required columns
            required_cols = ['f1', 'f2']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                raise ValueError(f"필수 열이 누락되었습니다: {missing_cols}. F1과 F2 열이 필요합니다.")
            
            # Optional vowel column
            if 'vowel' not in df.columns:
                df['vowel'] = 'unknown'
            
            # Rename to uppercase for consistency
            df = df.rename(columns={'f1': 'F1', 'f2': 'F2'})
        
        # Clean data
        df = df.dropna(subset=['F1', 'F2'])
        df['F1'] = pd.to_numeric(df['F1'], errors='coerce')
        df['F2'] = pd.to_numeric(df['F2'], errors='coerce')
        df = df.dropna(subset=['F1', 'F2'])
        
        # Filter reasonable formant values (100-4000 Hz)
        df = df[(df['F1'] >= 100) & (df['F1'] <= 4000)]
        df = df[(df['F2'] >= 100) & (df['F2'] <= 4000)]
        
        # Ensure vowel column exists
        if 'vowel' not in df.columns:
            df['vowel'] = 'unknown'
        
        if df.empty:
            raise ValueError("유효한 데이터가 없습니다. F1과 F2 값이 100-4000 Hz 범위에 있는지 확인하세요.")
        
        print(f"Successfully processed {len(df)} rows")  # Debug log
        
        if auto_detect and detection_info:
            return df, detection_info
        return df
    
    except Exception as e:
        print(f"Error processing CSV/XLSX/TXT: {e}")
        import traceback
        print(traceback.format_exc())
        if auto_detect:
            return pd.DataFrame(), None
        return pd.DataFrame()


def process_wav_textgrid(wav_files, textgrid_files=None):
    """
    Process WAV files and optional TextGrid files to extract formant data
    Returns a DataFrame with F1, F2, vowel labels, and time information
    """
    if parselmouth is None:
        print("Parselmouth not installed. Cannot process audio files.")
        return pd.DataFrame()
    
    all_data = []
    
    for wav_file in wav_files:
        try:
            # Load sound file
            sound = parselmouth.Sound(wav_file)
            
            # Find corresponding TextGrid if available
            textgrid = None
            textgrid_file = None
            if textgrid_files:
                base_name = wav_file.rsplit('.', 1)[0]
                for tg_file in textgrid_files:
                    if base_name in tg_file or tg_file.rsplit('.', 1)[0] == base_name:
                        textgrid_file = tg_file
                        break
                
                if textgrid_file:
                    textgrid = parselmouth.read(textgrid_file)
            
            # Extract formants
            formant = sound.to_formant_burg(
                time_step=0.01,
                max_number_of_formants=5,
                maximum_formant=5500.0,
                window_length=0.025,
                pre_emphasis_from=50.0
            )
            
            # If TextGrid is available, extract formants at labeled intervals
            if textgrid:
                data = extract_formants_from_textgrid(sound, formant, textgrid)
            else:
                # Extract formants at regular intervals
                data = extract_formants_regular(formant, sound.duration)
            
            all_data.extend(data)
        
        except Exception as e:
            print(f"Error processing {wav_file}: {e}")
            continue
    
    if not all_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_data)
    return df


def extract_formants_from_textgrid(sound, formant, textgrid):
    """Extract formants at labeled vowel intervals from TextGrid"""
    data = []
    
    try:
        # Get the first interval tier (assuming vowel labels are there)
        tier_names = [textgrid.get_tier_name(i+1) for i in range(textgrid.n_tiers)]
        vowel_tier_idx = 1  # Default to first tier
        
        # Try to find a tier with vowel-related names
        for idx, name in enumerate(tier_names, 1):
            if any(keyword in name.lower() for keyword in ['vowel', 'phone', 'segment']):
                vowel_tier_idx = idx
                break
        
        tier = call(textgrid, "Get tier", vowel_tier_idx)
        n_intervals = call(textgrid, "Get number of intervals", vowel_tier_idx)
        
        for i in range(1, n_intervals + 1):
            label = call(textgrid, "Get label of interval", vowel_tier_idx, i)
            
            if label and label.strip():  # Non-empty label
                start = call(textgrid, "Get start time of interval", vowel_tier_idx, i)
                end = call(textgrid, "Get end time of interval", vowel_tier_idx, i)
                
                # Sample formants at multiple time points within the interval
                duration = end - start
                if duration > 0.02:  # At least 20ms
                    # Sample at 25%, 50%, 75% of the interval
                    time_points = [start + duration * p for p in [0.25, 0.5, 0.75]]
                else:
                    time_points = [(start + end) / 2]
                
                for time_point in time_points:
                    f1 = call(formant, "Get value at time", 1, time_point, "hertz", "linear")
                    f2 = call(formant, "Get value at time", 2, time_point, "hertz", "linear")
                    
                    if f1 and f2 and not (np.isnan(f1) or np.isnan(f2)):
                        if 100 <= f1 <= 4000 and 100 <= f2 <= 4000:
                            data.append({
                                'vowel': label.strip(),
                                'F1': f1,
                                'F2': f2,
                                'time': time_point,
                                'duration': duration
                            })
    
    except Exception as e:
        print(f"Error extracting from TextGrid: {e}")
    
    return data


def extract_formants_regular(formant, duration):
    """Extract formants at regular intervals when no TextGrid is available"""
    data = []
    
    # Sample every 50ms
    time_step = 0.05
    time_points = np.arange(0.1, duration - 0.1, time_step)
    
    for time_point in time_points:
        f1 = call(formant, "Get value at time", 1, time_point, "hertz", "linear")
        f2 = call(formant, "Get value at time", 2, time_point, "hertz", "linear")
        
        if f1 and f2 and not (np.isnan(f1) or np.isnan(f2)):
            if 100 <= f1 <= 4000 and 100 <= f2 <= 4000:
                data.append({
                    'vowel': 'unlabeled',
                    'F1': f1,
                    'F2': f2,
                    'time': time_point
                })
    
    return data
