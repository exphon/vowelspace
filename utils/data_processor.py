"""
Data processing utilities for handling CSV, XLSX, WAV, and TextGrid files
"""
import pandas as pd
import numpy as np
import os
import re
import unicodedata
try:
    import parselmouth
    from parselmouth.praat import call
except ImportError:
    parselmouth = None

from .column_detector import auto_detect_and_rename, ColumnDetector


# ----------------------------
# Vowel label utilities
# ----------------------------
ARPABET_VOWELS = {
    'AA','AE','AH','AO','AW','AY','EH','ER','EY','IH','IY','OW','OY','UH','UW','UX'
}

# IPA vowel characters set (lowercase) for quick membership tests
IPA_VOWEL_CHARS = set(
    list('aeiouy') + list('ɪʊəɚɝɜɞʌɔɑæɒɛøœɶɨɯʏɐɤɵ') + list('iu y')
)

def _strip_diacritics(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def is_vowel_label(label: str) -> bool:
    """Return True if a label looks like a vowel phone (ARPABET or IPA).

    Handles:
    - ARPABET with stress digits (e.g., AH0, IY1)
    - IPA with length marks (:, ː) and stress marks (ˈ, ˌ)
    - Removes diacritics before checking
    """
    if not label:
        return False
    s = str(label).strip()
    if not s:
        return False
    # Remove common prosodic marks and length marks
    s = s.replace('ˈ', '').replace('ˌ', '').replace('ː', '').replace(':', '')
    s = _strip_diacritics(s)

    # Check ARPABET (uppercase, remove digits)
    arp = re.sub(r'\d', '', s.upper())
    if arp in ARPABET_VOWELS:
        return True

    # Check IPA/roman vowels: keep only letters and IPA vowel symbols
    cleaned = re.sub(r"[^A-Za-zɪʊəɚɝɜɞʌɔɑæɒɛøœɶɨɯʏɐɤɵ]", '', s)
    cleaned = cleaned.lower()
    if cleaned and all(ch in IPA_VOWEL_CHARS for ch in cleaned):
        return True

    return False


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
    Returns a tuple: (DataFrame with F1, F2, vowel labels, and time information, metadata dict)
    """
    if parselmouth is None:
        print("Parselmouth not installed. Cannot process audio files.")
        return pd.DataFrame(), None
    
    all_data = []
    metadata = {
        'files': [],
        'total_vowels_extracted': 0,
        'vowel_counts': {},
        'processing_info': []
    }
    
    for wav_file in wav_files:
        try:
            # Extract metadata from filename
            basename = os.path.splitext(os.path.basename(wav_file))[0]
            
            # Try to extract speaker and language from filename patterns
            # Common patterns: speaker_language_*, language_speaker_*, etc.
            file_metadata = extract_metadata_from_filename(basename)
            
            # Load sound file
            sound = parselmouth.Sound(wav_file)
            
            # Check and resample to 16000 Hz if needed
            original_sampling_rate = sound.sampling_frequency
            target_sampling_rate = 16000
            
            if original_sampling_rate != target_sampling_rate:
                print(f"Resampling {basename} from {original_sampling_rate} Hz to {target_sampling_rate} Hz")
                sound = sound.resample(target_sampling_rate, precision=50)
                metadata['processing_info'].append(
                    f"  ↻ Resampled from {original_sampling_rate} Hz to {target_sampling_rate} Hz"
                )
            else:
                print(f"{basename}: Already at {target_sampling_rate} Hz")
            
            # Find corresponding TextGrid if available
            textgrid = None
            textgrid_file = None
            if textgrid_files:
                base_name = os.path.splitext(wav_file)[0]
                basename_only = os.path.basename(base_name)
                for tg_file in textgrid_files:
                    tg_base = os.path.splitext(os.path.basename(tg_file))[0]
                    if basename_only == tg_base:
                        textgrid_file = tg_file
                        break
                
                if textgrid_file:
                    try:
                        textgrid = parselmouth.read(textgrid_file)
                    except Exception as e:
                        print(f"Error reading TextGrid {textgrid_file}: {e}")
            
            # Extract formants
            formant = sound.to_formant_burg(
                time_step=0.01,
                max_number_of_formants=5,
                maximum_formant=5500.0,
                window_length=0.025,
                pre_emphasis_from=50.0
            )
            
            # If TextGrid is available, extract formants at labeled intervals
            file_data = []
            if textgrid:
                file_data = extract_formants_from_textgrid(sound, formant, textgrid, file_metadata, basename)
            else:
                file_data = extract_formants_regular(formant, sound.duration, file_metadata, basename)
            
            # Track statistics
            vowel_count = len(file_data)
            metadata['files'].append({
                'wav_file': os.path.basename(wav_file),
                'textgrid_file': os.path.basename(textgrid_file) if textgrid_file else None,
                'basename': basename,
                'duration': sound.duration,
                'original_sampling_rate': original_sampling_rate,
                'final_sampling_rate': sound.sampling_frequency,
                'was_resampled': original_sampling_rate != target_sampling_rate,
                'vowels_extracted': vowel_count,
                **file_metadata
            })
            
            metadata['total_vowels_extracted'] += vowel_count
            
            # Count vowels
            for item in file_data:
                vowel = item.get('vowel', 'unknown')
                metadata['vowel_counts'][vowel] = metadata['vowel_counts'].get(vowel, 0) + 1
            
            all_data.extend(file_data)
            metadata['processing_info'].append(f"✓ {basename}: {vowel_count} vowels")
        
        except Exception as e:
            error_msg = f"✗ {os.path.basename(wav_file)}: {str(e)}"
            print(f"Error processing {wav_file}: {e}")
            metadata['processing_info'].append(error_msg)
            continue
    
    if not all_data:
        return pd.DataFrame(), metadata
    
    df = pd.DataFrame(all_data)
    
    # Keep only vowel-labeled rows
    if 'vowel' in df.columns:
        df = df[df['vowel'].apply(is_vowel_label)]
    
    # Ensure required columns exist
    if 'speaker' not in df.columns:
        df['speaker'] = 'unknown'
    if 'native_language' not in df.columns:
        df['native_language'] = 'unknown'

    # Normalize speaker and language fields so grouping logic never sees NaN/None
    df['speaker'] = (
        df['speaker']
        .fillna('unknown')
        .replace('', 'unknown')
        .astype(str)
    )
    df['native_language'] = (
        df['native_language']
        .fillna('unknown')
        .replace('', 'unknown')
        .astype(str)
    )
    
    return df, metadata


def extract_metadata_from_filename(basename):
    """
    Extract metadata (speaker, language) from filename
    Common patterns:
    - speaker_language_*
    - language_speaker_*
    - speaker-language-*
    - just_speaker
    """
    metadata = {
        'speaker': None,
        'native_language': None
    }
    
    # Split by common delimiters
    parts = basename.replace('-', '_').replace('.', '_').split('_')
    
    # Try to identify speaker and language
    if len(parts) >= 2:
        # Assume first two parts might be speaker and language
        metadata['speaker'] = parts[0]
        metadata['native_language'] = parts[1]
    elif len(parts) == 1:
        metadata['speaker'] = parts[0]
    
    # If no metadata found, use basename as speaker
    if not metadata['speaker']:
        metadata['speaker'] = basename
    
    return metadata


def extract_formants_from_textgrid(sound, formant, textgrid, file_metadata, basename):
    """Extract formants at labeled vowel intervals from TextGrid"""
    data = []
    
    try:
        # Get the number of tiers and their names using Praat calls
        n_tiers = int(call(textgrid, "Get number of tiers"))
        tier_names = [call(textgrid, "Get tier name", i) for i in range(1, n_tiers + 1)]
        vowel_tier_idx = 1  # Default to first tier
        
        # Try to find a tier with vowel-related names
        for idx, name in enumerate(tier_names, 1):
            if name and any(keyword in str(name).lower() for keyword in ['vowel', 'phone', 'segment']):
                vowel_tier_idx = idx
                break
        
        # Get number of intervals in the selected tier
        n_intervals = int(call(textgrid, "Get number of intervals", vowel_tier_idx))
        
        for i in range(1, n_intervals + 1):
            label = call(textgrid, "Get label of interval", vowel_tier_idx, i)
            
            if label and label.strip():  # Non-empty label
                start = call(textgrid, "Get start time of interval", vowel_tier_idx, i)
                end = call(textgrid, "Get end time of interval", vowel_tier_idx, i)
                
                # Sample formants from the middle 25% of the duration
                duration = end - start
                if duration > 0.02:  # At least 20ms
                    # Calculate middle 25% range: from 37.5% to 62.5% of duration
                    mid_start = start + duration * 0.375
                    mid_end = start + duration * 0.625
                    
                    # Sample at 5 points within the middle 25% and average them
                    time_points = np.linspace(mid_start, mid_end, 5)
                    
                    f1_values = []
                    f2_values = []
                    
                    for time_point in time_points:
                        f1 = call(formant, "Get value at time", 1, time_point, "hertz", "linear")
                        f2 = call(formant, "Get value at time", 2, time_point, "hertz", "linear")
                        
                        if f1 and f2 and not (np.isnan(f1) or np.isnan(f2)):
                            if 100 <= f1 <= 4000 and 100 <= f2 <= 4000:
                                f1_values.append(f1)
                                f2_values.append(f2)
                    
                    # Use average values if we have valid measurements
                    if f1_values and f2_values and is_vowel_label(label):
                        f1_avg = np.mean(f1_values)
                        f2_avg = np.mean(f2_values)
                        mid_time = (mid_start + mid_end) / 2
                        
                        data_point = {
                            'vowel': label.strip(),
                            'F1': round(f1_avg, 1),
                            'F2': round(f2_avg, 1),
                            'time': mid_time,
                            'duration': duration * 1000,  # Convert to ms
                            'file': basename
                        }
                        # Add metadata
                        if file_metadata.get('speaker'):
                            data_point['speaker'] = file_metadata['speaker']
                        if file_metadata.get('native_language'):
                            data_point['native_language'] = file_metadata['native_language']
                        
                        data.append(data_point)
                else:
                    # For very short segments, use midpoint
                    time_point = (start + end) / 2
                    f1 = call(formant, "Get value at time", 1, time_point, "hertz", "linear")
                    f2 = call(formant, "Get value at time", 2, time_point, "hertz", "linear")
                    
                    if f1 and f2 and not (np.isnan(f1) or np.isnan(f2)):
                        if 100 <= f1 <= 4000 and 100 <= f2 <= 4000 and is_vowel_label(label):
                            data_point = {
                                'vowel': label.strip(),
                                'F1': round(f1, 1),
                                'F2': round(f2, 1),
                                'time': time_point,
                                'duration': duration * 1000,  # Convert to ms
                                'file': basename
                            }
                            # Add metadata
                            if file_metadata.get('speaker'):
                                data_point['speaker'] = file_metadata['speaker']
                            if file_metadata.get('native_language'):
                                data_point['native_language'] = file_metadata['native_language']
                            
                            data.append(data_point)
    
    except Exception as e:
        print(f"Error extracting from TextGrid: {e}")
    
    return data


def extract_formants_regular(formant, duration, file_metadata, basename):
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
                data_point = {
                    'vowel': 'unlabeled',
                    'F1': round(f1, 1),
                    'F2': round(f2, 1),
                    'time': time_point,
                    'file': basename
                }
                # Add metadata
                if file_metadata.get('speaker'):
                    data_point['speaker'] = file_metadata['speaker']
                if file_metadata.get('native_language'):
                    data_point['native_language'] = file_metadata['native_language']
                
                data.append(data_point)
    
    return data
