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

ARPABET_TO_IPA = {
    'AA': 'ɑ',
    'AE': 'æ',
    'AH': 'ʌ',
    'AO': 'ɔ',
    'AW': 'aʊ',
    'AY': 'aɪ',
    'EH': 'ɛ',
    'ER': 'ɝ',
    'EY': 'eɪ',
    'IH': 'ɪ',
    'IY': 'i',
    'OW': 'oʊ',
    'OY': 'ɔɪ',
    'UH': 'ʊ',
    'UW': 'u',
    'UX': 'ʉ',
}

# IPA vowel characters set (lowercase) for quick membership tests
IPA_VOWEL_CHARS = set('aeiouɪʊəɚɝɜɞʌɔɑæɒɛøœɶɨɯʏɐɤɵ') | {'j', 'w', 'y'}

# Korean romanized vowel tokens mapped to IPA approximations
KOREAN_VOWEL_TO_IPA = {
    'a': 'a',
    'ae': 'ɛ',
    'e': 'e',
    'eo': 'ʌ',
    'eu': 'ɯ',
    'i': 'i',
    'o': 'o',
    'oe': 'we',
    'u': 'u',
    'wa': 'wa',
    'wae': 'wɛ',
    'we': 'we',
    'weo': 'wʌ',
    'wi': 'wi',
    'ya': 'ja',
    'yae': 'jɛ',
    'ye': 'je',
    'yeo': 'jʌ',
    'yi': 'ɯi',
    'yo': 'jo',
    'yu': 'ju',
}

CORE_VOWELS_ENGLISH_IPA = {'ɑ', 'eɪ', 'i', 'oʊ', 'u'}
CORE_VOWELS_KOREAN_IPA = {'a', 'e', 'i', 'o', 'u'}
CORE_VOWELS_IPA = CORE_VOWELS_ENGLISH_IPA | CORE_VOWELS_KOREAN_IPA
CORE_VOWELS_IPA_NORMALIZED = {v.lower() for v in CORE_VOWELS_IPA}

_NUMERIC_SUFFIX_RE = re.compile(r'\d+$')


def normalize_vowel_label(label):
    if label is None:
        return ''
    if isinstance(label, float) and np.isnan(label):
        return ''
    s = str(label).strip()
    if not s or s.lower() == 'nan':
        return ''
    return _NUMERIC_SUFFIX_RE.sub('', s)

def _strip_diacritics(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def convert_to_ipa_label(label):
    normalized = normalize_vowel_label(label)
    if not normalized:
        return normalized
    mapped = ARPABET_TO_IPA.get(normalized.upper())
    if mapped:
        return mapped
    korean_mapped = KOREAN_VOWEL_TO_IPA.get(normalized.lower())
    return korean_mapped if korean_mapped else normalized


def is_core_vowel_label(label: str) -> bool:
    ipa_label = convert_to_ipa_label(label)
    if not ipa_label:
        return False
    return ipa_label.strip().lower() in CORE_VOWELS_IPA_NORMALIZED

def is_vowel_label(label: str) -> bool:
    """Return True if a label looks like a vowel phone (ARPABET or IPA).

    Handles:
    - ARPABET with stress digits (e.g., AH0, IY1)
    - IPA with length marks (:, ː) and stress marks (ˈ, ˌ)
    - Removes diacritics before checking
    """
    s = normalize_vowel_label(label)
    if not s:
        return False
    # Remove common prosodic marks and length marks
    s = s.replace('ˈ', '').replace('ˌ', '').replace('ː', '').replace(':', '')
    s = _strip_diacritics(s)

    # Check ARPABET (uppercase, remove digits)
    arp = s.upper()
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
        df['vowel'] = df['vowel'].apply(normalize_vowel_label)
        df['vowel_raw'] = df['vowel']
        df['vowel'] = df['vowel'].replace('', 'unknown')
        df['vowel'] = df['vowel'].apply(convert_to_ipa_label)
        
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


TARGET_SAMPLING_RATE = 16000


def process_wav_textgrid(wav_files, textgrid_files=None, ceiling_mode='auto',
                         fixed_ceiling=5500.0, ceiling_criterion='f3f4'):
    """
    Process WAV files and optional TextGrid files to extract formant data.

    Args:
        wav_files: list of WAV paths
        textgrid_files: list of TextGrid paths (matched to WAVs by basename)
        ceiling_mode: 'auto' optimises the formant ceiling per speaker
                      (see utils.formant_ceiling); 'fixed' uses ``fixed_ceiling``.
        fixed_ceiling: ceiling in Hz used when ``ceiling_mode == 'fixed'`` and
                       as the fallback when optimisation is impossible.
        ceiling_criterion: 'f3f4' (default), 'f1f2' (Escudero et al. 2009) or
                           'combined'.

    Returns a tuple: (DataFrame with F1-F4, vowel labels, time information and
    the ceiling used, metadata dict)
    """
    if parselmouth is None:
        print("Parselmouth not installed. Cannot process audio files.")
        return pd.DataFrame(), None

    from .formant_ceiling import compute_formant, measure_token, optimize_ceiling, CRITERIA

    if ceiling_criterion not in CRITERIA:
        ceiling_criterion = 'f3f4'
    try:
        fixed_ceiling = float(fixed_ceiling)
    except (TypeError, ValueError):
        fixed_ceiling = 5500.0
    if ceiling_mode != 'auto':
        ceiling_mode = 'fixed'

    metadata = {
        'files': [],
        'total_vowels_extracted': 0,
        'vowel_counts': {},
        'processing_info': [],
        'formant_ceiling': {
            'mode': ceiling_mode,
            'criterion': ceiling_criterion if ceiling_mode == 'auto' else None,
            'fixed_ceiling': fixed_ceiling if ceiling_mode == 'fixed' else None,
            'speakers': {},
        },
    }

    # ---- Pass 1: load audio, find TextGrids, collect vowel tokens ----
    entries = []
    for wav_file in wav_files:
        basename = os.path.splitext(os.path.basename(wav_file))[0]
        try:
            file_metadata = extract_metadata_from_filename(basename)
            sound = parselmouth.Sound(wav_file)

            original_sampling_rate = sound.sampling_frequency
            if original_sampling_rate != TARGET_SAMPLING_RATE:
                print(f"Resampling {basename} from {original_sampling_rate} Hz to {TARGET_SAMPLING_RATE} Hz")
                sound = sound.resample(TARGET_SAMPLING_RATE, precision=50)
                metadata['processing_info'].append(
                    f"  ↻ Resampled from {original_sampling_rate} Hz to {TARGET_SAMPLING_RATE} Hz"
                )

            textgrid_file = _find_textgrid(wav_file, textgrid_files)
            textgrid = None
            if textgrid_file:
                try:
                    textgrid = parselmouth.read(textgrid_file)
                except Exception as e:
                    print(f"Error reading TextGrid {textgrid_file}: {e}")

            if textgrid is not None:
                tokens = collect_vowel_tokens(textgrid)
            else:
                tokens = collect_voiced_frames(sound)

            entries.append({
                'basename': basename,
                'wav_file': wav_file,
                'textgrid_file': textgrid_file,
                'sound': sound,
                'tokens': tokens,
                'file_metadata': file_metadata,
                'original_sampling_rate': original_sampling_rate,
                'speaker_key': file_metadata.get('speaker') or basename,
            })
        except Exception as e:
            print(f"Error loading {wav_file}: {e}")
            metadata['processing_info'].append(f"✗ {os.path.basename(wav_file)}: {e}")

    # ---- Pass 2: choose a ceiling per speaker ----
    speaker_ceiling = {}
    if ceiling_mode == 'auto':
        groups = {}
        for entry in entries:
            groups.setdefault(entry['speaker_key'], []).append(entry)
        for speaker, group in groups.items():
            items = [(e['sound'], e['tokens']) for e in group]
            try:
                result = optimize_ceiling(items, criterion=ceiling_criterion, fallback=fixed_ceiling)
            except Exception as e:
                print(f"Ceiling optimisation failed for {speaker}: {e}")
                result = {'ceiling': fixed_ceiling, 'criterion': None, 'score': None,
                          'n_tokens': sum(len(e['tokens']) for e in group), 'sweep': [],
                          'note': f'optimisation failed ({e}); fixed ceiling used'}
            speaker_ceiling[speaker] = result['ceiling']
            metadata['formant_ceiling']['speakers'][speaker] = {
                **result,
                'files': [e['basename'] for e in group],
            }
            crit = result.get('criterion') or 'fixed'
            metadata['processing_info'].append(
                f"⚙ {speaker}: formant ceiling {result['ceiling']:.0f} Hz "
                f"({crit}, {result['n_tokens']} tokens)"
            )
    else:
        for entry in entries:
            speaker_ceiling[entry['speaker_key']] = fixed_ceiling

    # ---- Pass 3: extract formants with the chosen ceiling ----
    all_data = []
    for entry in entries:
        basename = entry['basename']
        ceiling = speaker_ceiling.get(entry['speaker_key'], fixed_ceiling)
        try:
            formant = compute_formant(entry['sound'], ceiling)
            file_data = extract_token_formants(formant, entry['tokens'], entry['file_metadata'],
                                               basename, ceiling, measure_token)
            vowel_count = len(file_data)
            metadata['files'].append({
                'wav_file': os.path.basename(entry['wav_file']),
                'textgrid_file': os.path.basename(entry['textgrid_file']) if entry['textgrid_file'] else None,
                'basename': basename,
                'duration': entry['sound'].duration,
                'original_sampling_rate': entry['original_sampling_rate'],
                'final_sampling_rate': entry['sound'].sampling_frequency,
                'was_resampled': entry['original_sampling_rate'] != TARGET_SAMPLING_RATE,
                'formant_ceiling': ceiling,
                'vowels_extracted': vowel_count,
                **entry['file_metadata'],
            })
            metadata['total_vowels_extracted'] += vowel_count
            for item in file_data:
                vowel = item.get('vowel') or convert_to_ipa_label(item.get('vowel_raw', 'unknown'))
                metadata['vowel_counts'][vowel] = metadata['vowel_counts'].get(vowel, 0) + 1
            all_data.extend(file_data)
            metadata['processing_info'].append(f"✓ {basename}: {vowel_count} vowels (ceiling {ceiling:.0f} Hz)")
        except Exception as e:
            print(f"Error processing {entry['wav_file']}: {e}")
            metadata['processing_info'].append(f"✗ {os.path.basename(entry['wav_file'])}: {e}")

    if not all_data:
        return pd.DataFrame(), metadata

    df = pd.DataFrame(all_data)

    # Keep only vowel-labeled rows ('unlabeled' = voiced frames of a WAV without TextGrid)
    def _keep(label):
        return label == 'unlabeled' or is_vowel_label(label)

    def _ipa(label):
        return label if label == 'unlabeled' else convert_to_ipa_label(label)

    if 'vowel_raw' in df.columns:
        df['vowel_raw'] = df['vowel_raw'].apply(normalize_vowel_label)
        df = df[df['vowel_raw'].apply(_keep)].copy()
        df['vowel'] = df['vowel_raw'].apply(_ipa)
    elif 'vowel' in df.columns:
        df['vowel'] = df['vowel'].apply(normalize_vowel_label)
        df = df[df['vowel'].apply(_keep)].copy()
        df['vowel'] = df['vowel'].apply(_ipa)

    # Ensure required columns exist
    if 'speaker' not in df.columns:
        df['speaker'] = 'unknown'
    if 'native_language' not in df.columns:
        df['native_language'] = 'unknown'

    # Normalize speaker and language fields so grouping logic never sees NaN/None
    df['speaker'] = df['speaker'].fillna('unknown').replace('', 'unknown').astype(str)
    df['native_language'] = df['native_language'].fillna('unknown').replace('', 'unknown').astype(str)

    return df, metadata


def _find_textgrid(wav_file, textgrid_files):
    """Return the TextGrid path whose basename matches the WAV, if any."""
    if not textgrid_files:
        return None
    basename_only = os.path.splitext(os.path.basename(wav_file))[0]
    for tg_file in textgrid_files:
        if os.path.splitext(os.path.basename(tg_file))[0] == basename_only:
            return tg_file
    return None


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


def find_vowel_tier(textgrid):
    """Index (1-based) of the tier most likely to hold vowel/phone labels."""
    n_tiers = int(call(textgrid, "Get number of tiers"))
    tier_names = [call(textgrid, "Get tier name", i) for i in range(1, n_tiers + 1)]
    for idx, name in enumerate(tier_names, 1):
        if name and any(keyword in str(name).lower() for keyword in ['vowel', 'phone', 'segment']):
            return idx
    return 1


def collect_vowel_tokens(textgrid):
    """
    Vowel intervals of a TextGrid as a list of dicts:
    ``{'vowel': ipa, 'vowel_raw': clean_label, 'start': s, 'end': e}``.
    """
    tokens = []
    try:
        tier = find_vowel_tier(textgrid)
        n_intervals = int(call(textgrid, "Get number of intervals", tier))
        for i in range(1, n_intervals + 1):
            label = call(textgrid, "Get label of interval", tier, i)
            if not label or not label.strip():
                continue
            clean_label = normalize_vowel_label(label)
            if not is_vowel_label(clean_label):
                continue
            start = call(textgrid, "Get start time of interval", tier, i)
            end = call(textgrid, "Get end time of interval", tier, i)
            if end - start <= 0:
                continue
            tokens.append({
                'vowel': convert_to_ipa_label(clean_label),
                'vowel_raw': clean_label,
                'start': start,
                'end': end,
            })
    except Exception as e:
        print(f"Error reading TextGrid intervals: {e}")
    return tokens


def collect_voiced_frames(sound, time_step=0.05, margin=0.1):
    """
    Regularly spaced voiced frames for a sound without a TextGrid.

    Frames every ``time_step`` seconds whose pitch is defined are returned as
    zero-length tokens labelled 'unlabeled' (measured at the frame time only).
    """
    tokens = []
    try:
        pitch = sound.to_pitch()
    except Exception:
        pitch = None
    for t in np.arange(margin, sound.duration - margin, time_step):
        if pitch is not None:
            f0 = call(pitch, "Get value at time", float(t), "Hertz", "linear")
            if f0 is None or np.isnan(f0):
                continue
        tokens.append({'vowel': 'unlabeled', 'vowel_raw': 'unlabeled', 'start': float(t), 'end': float(t)})
    return tokens


def extract_token_formants(formant, tokens, file_metadata, basename, ceiling, measure_token):
    """
    Measure F1-F4 for each token with an already computed Formant object.

    Tokens are measured over the middle 25% of their duration (5 points,
    averaged); zero-length or very short tokens at their midpoint. Tokens whose
    F1 or F2 fall outside 100-4000 Hz are dropped.
    """
    data = []
    for tok in tokens:
        values = measure_token(formant, tok['start'], tok['end'])
        f1, f2, f3, f4 = values
        if np.isnan(f1) or np.isnan(f2):
            continue
        if not (100 <= f1 <= 4000 and 100 <= f2 <= 4000):
            continue
        duration = tok['end'] - tok['start']
        data_point = {
            'vowel': tok.get('vowel') or 'unlabeled',
            'vowel_raw': tok.get('vowel_raw') or 'unlabeled',
            'F1': round(float(f1), 1),
            'F2': round(float(f2), 1),
            'F3': None if np.isnan(f3) else round(float(f3), 1),
            'F4': None if np.isnan(f4) else round(float(f4), 1),
            'time': (tok['start'] + tok['end']) / 2.0,
            'file': basename,
            'formant_ceiling': float(ceiling),
        }
        if duration > 0:
            data_point['duration'] = duration * 1000  # ms
        if file_metadata.get('speaker'):
            data_point['speaker'] = file_metadata['speaker']
        if file_metadata.get('native_language'):
            data_point['native_language'] = file_metadata['native_language']
        data.append(data_point)
    return data
