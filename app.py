from flask import Flask, render_template, request, jsonify, send_file
from flask_login import current_user
import os
import functools
from werkzeug.middleware.proxy_fix import ProxyFix
import json
import traceback
import numpy as np
import pandas as pd
from pathlib import Path
from zipfile import ZipFile
import io
from utils.data_processor import (
    process_csv_xlsx,
    process_wav_textgrid,
    CORE_VOWELS_ENGLISH_IPA,
    CORE_VOWELS_KOREAN_IPA,
    CORE_VOWELS_IPA_NORMALIZED,
    convert_to_ipa_label,
)
from utils.visualizer import (
    create_static_vowel_space, 
    create_dynamic_formant_trajectory,
    create_formant_time_trajectory,
    create_vowel_space_with_ellipses,
    create_group_comparison_plot,
    create_pca_plot,
    create_lda_plot,
    create_boxplot,
    create_violin_plot,
    create_histogram,
    create_scatter_matrix,
    create_mean_comparison_plot,
    create_pairwise_comparison_plot
)
from utils.statistics import perform_comprehensive_analysis
from utils.formant_scales import convert_formants, get_scale_label, get_available_scales
from auth import init_auth
from workspace import Workspace, purge_expired

CORE_VOWEL_DISPLAY_INFO = {
    'english_ipa': sorted(CORE_VOWELS_ENGLISH_IPA),
    'korean_ipa': sorted(CORE_VOWELS_KOREAN_IPA),
}


def convert_to_json_serializable(obj):
    """Convert numpy types to native Python types for JSON serialization"""
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, str):
        return obj
    elif obj is None:
        return None
    else:
        return obj


def remove_outliers_by_vowel(df, std_threshold=3):
    """
    Remove outliers from formant data on a per-vowel basis.
    Values beyond ±std_threshold standard deviations from the mean are removed.
    
    Args:
        df: DataFrame with 'vowel', 'F1', 'F2' columns
        std_threshold: Number of standard deviations for outlier detection (default: 3)
    
    Returns:
        DataFrame with outliers removed
    """
    if df.empty or 'vowel' not in df.columns:
        return df
    
    cleaned_rows = []
    
    for vowel in df['vowel'].unique():
        vowel_data = df[df['vowel'] == vowel].copy()
        
        if len(vowel_data) < 3:  # Need at least 3 points for meaningful stats
            cleaned_rows.append(vowel_data)
            continue
        
        # Calculate mean and std for F1 and F2
        f1_mean = vowel_data['F1'].mean()
        f1_std = vowel_data['F1'].std()
        f2_mean = vowel_data['F2'].mean()
        f2_std = vowel_data['F2'].std()
        
        # Filter: keep only values within ±3 standard deviations
        mask = (
            (np.abs(vowel_data['F1'] - f1_mean) <= std_threshold * f1_std) &
            (np.abs(vowel_data['F2'] - f2_mean) <= std_threshold * f2_std)
        )
        
        cleaned_vowel_data = vowel_data[mask]
        cleaned_rows.append(cleaned_vowel_data)
    
    if cleaned_rows:
        result = pd.concat(cleaned_rows, ignore_index=True)
        return result
    else:
        return df


def filter_basic_vowels(df):
    """Keep only rows whose vowels map to the core IPA set."""
    if df is None or df.empty:
        return df

    if 'vowel' in df.columns:
        source = df['vowel']
    elif 'vowel_raw' in df.columns:
        source = df['vowel_raw']
    else:
        return df

    ipa_series = source.fillna('').astype(str).apply(lambda value: convert_to_ipa_label(value).strip().lower())
    mask = ipa_series.isin(CORE_VOWELS_IPA_NORMALIZED)

    if not mask.any():
        return df.iloc[0:0].copy()

    filtered = df.loc[mask].copy()

    # Ensure the vowel column reflects IPA values from the filtered set
    if 'vowel' in filtered.columns:
        filtered.loc[:, 'vowel'] = filtered['vowel'].astype(str).apply(convert_to_ipa_label)
    else:
        filtered.loc[:, 'vowel'] = source.loc[mask].apply(convert_to_ipa_label)

    return filtered


app = Flask(__name__)
# nginx 리버스 프록시 뒤에서 X-Forwarded-* 헤더를 신뢰
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size for WAV/TextGrid
# Uploads accumulate until the user deletes them; this caps what one user can keep
MAX_STORED_BYTES = int(float(os.environ.get('UPLOAD_MAX_TOTAL_MB', '500')) * 1024 * 1024)
SPREADSHEET_EXTS = ('csv', 'xlsx', 'xls', 'txt')
app.config['ALLOWED_EXTENSIONS'] = {'wav', 'TextGrid', 'textgrid', 'csv', 'xlsx', 'xls', 'txt'}

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# Accounts: every route below requires a logged-in user (see auth.py)
init_auth(app)


class UploadError(Exception):
    """A problem with the uploaded files that is reported to the user."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def with_workspace(view):
    """
    Run a view with the current user's private upload folder as first argument.

    Requests of one user are serialized, and folders nobody has used for the
    retention period are removed on the way.
    """
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        purge_expired(app.config['UPLOAD_FOLDER'])
        workspace = Workspace(app.config['UPLOAD_FOLDER'], current_user.get_id())
        with workspace.locked():
            workspace.touch()
            return view(workspace, *args, **kwargs)
    return wrapper


def pairing_problem(files):
    """Why the WAV/TextGrid files in ``files`` cannot be analysed, or None."""
    wav = {os.path.splitext(f['name'])[0] for f in files if f['ext'] == 'wav'}
    textgrid = {os.path.splitext(f['name'])[0] for f in files if f['ext'] == 'textgrid'}
    if wav == textgrid:
        return None
    message = 'Each WAV file needs a TextGrid file with the same name (and the other way round). '
    if wav - textgrid:
        message += f'TextGrid missing for: {", ".join(sorted(wav - textgrid))}. '
    if textgrid - wav:
        message += f'WAV missing for: {", ".join(sorted(textgrid - wav))}.'
    return message.strip()


def check_stored_set(files):
    """Reject an upload that would leave unpaired audio or exceed the storage cap."""
    problem = pairing_problem(files)
    if problem:
        raise UploadError(problem + ' Nothing was uploaded; the files already on the server are unchanged.')
    total = sum(f['size'] for f in files)
    if total > MAX_STORED_BYTES:
        raise UploadError(
            f'These files would bring your stored files to {total / 1048576:.0f} MB; the limit is '
            f'{MAX_STORED_BYTES / 1048576:.0f} MB. Delete some uploaded files first. Nothing was uploaded.')


def load_wav_textgrid(workspace, wav_files, textgrid_files, ceiling_options):
    """Formant measurements of the stored WAV/TextGrid pairs (cached per ceiling setting)."""
    mode, fixed_ceiling, criterion, scope = ceiling_options or ('auto', 5500.0, 'f3f4', 'speaker')
    options = {'mode': mode, 'fixed_ceiling': fixed_ceiling, 'criterion': criterion, 'scope': scope}
    cached = workspace.load_measurements(options)
    if cached is not None:
        data, metadata = cached
        print(f"Re-using cached formant measurements ({len(data)} rows)")
        return data, metadata

    print(f"Processing {len(wav_files)} WAV/TextGrid pairs")
    by_name = {os.path.splitext(f['name'])[0]: f['path'] for f in textgrid_files}
    wav_paths = [f['path'] for f in wav_files]
    textgrid_paths = [by_name[os.path.splitext(f['name'])[0]] for f in wav_files]
    result = process_wav_textgrid(
        wav_paths, textgrid_paths,
        ceiling_mode=mode,
        fixed_ceiling=fixed_ceiling,
        ceiling_criterion=criterion,
        ceiling_scope=scope,
    )
    data, metadata = result if isinstance(result, tuple) else (result, None)
    if data is not None and not data.empty:
        workspace.save_measurements(options, data, metadata)
    return data, metadata


def save_extracted_csv(workspace, data):
    """Keep the measured tokens for the "download extracted data" button."""
    csv_path = workspace.cache_path('last_extracted_data.csv')
    data = data.drop(columns=['upload_set'], errors='ignore')
    data.sort_values(by=['vowel', 'F1'], ascending=[True, True]).to_csv(csv_path, index=False)
    print(f"Extracted data saved to {csv_path} (sorted by vowel and F1)")


def combine_datasets(parts):
    """
    One table from several data sets (``parts`` is a list of (label, DataFrame)).

    The sets stay distinguishable in the plots: a set without a speaker and
    without a native_language column gets its file name as speaker, and gaps
    that appear because only some sets have one of these columns are filled
    with the file name too (rows without a group value would be dropped from
    the grouped plots).
    """
    frames = []
    for label, frame in parts:
        frame = frame.copy()
        if 'speaker' not in frame.columns and 'native_language' not in frame.columns:
            frame['speaker'] = label
        frame['_dataset'] = label
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True, sort=False)
    for column in ('speaker', 'native_language'):
        if column in data.columns:
            data[column] = data[column].where(data[column].notna(), data['_dataset'])
    return data.drop(columns='_dataset')


def load_user_data(workspace, ceiling_options=None):
    """
    Formant data from all files the user has on the server.

    Files sent with the request are added to the stored set first (a file
    with the same name is replaced); a request without files re-uses what is
    stored, so parameters can be changed without uploading again and data
    sets uploaded at different times are plotted together. Formant tables
    (CSV/TXT/XLSX) and WAV/TextGrid measurements can be mixed.

    Returns (data, detection_info, metadata, data_source); data may be None or
    empty when nothing could be read. data_source is 'csv' (tables only),
    'wav_textgrid' (audio only) or 'mixed'; in the mixed case outliers are
    already removed from the audio part and its CSV is saved.
    Raises UploadError for unusable input.
    """
    uploads = [f for f in request.files.getlist('files') if f and f.filename]
    if uploads and not workspace.add_files(uploads, allowed_file, check=check_stored_set,
                                           label=request.form.get('set_label')):
        raise UploadError('File format not allowed.')

    stored = workspace.files()
    if not stored:
        raise UploadError('Please select a file.')

    problem = pairing_problem(stored)
    if problem:
        raise UploadError(problem)

    spreadsheets = [f for f in stored if f['ext'] in SPREADSHEET_EXTS]
    wav_files = [f for f in stored if f['ext'] == 'wav']
    textgrid_files = [f for f in stored if f['ext'] == 'textgrid']
    if not spreadsheets and not wav_files:
        raise UploadError('Unsupported file combination.')

    # Every row remembers the upload set of its file, so sets can be compared
    set_labels = {name: label for name, (_, label) in workspace.file_sets().items()}
    tables, detection_info = [], None
    for f in spreadsheets:
        result = process_csv_xlsx(f['path'], auto_detect=True)
        frame, info = result if isinstance(result, tuple) else (result, None)
        if frame is None or frame.empty:
            if len(stored) == 1:
                return frame, info, None, 'csv'
            raise UploadError(
                f'"{f["name"]}" could not be read as formant data (it needs F1 and F2 columns). '
                f'Delete it from the uploaded files or upload a corrected version.')
        frame = frame.copy()
        frame['upload_set'] = set_labels[f['name']]
        tables.append((os.path.splitext(f['name'])[0], frame))
        detection_info = detection_info or info

    if not wav_files:
        if len(tables) == 1:
            return tables[0][1], detection_info, None, 'csv'
        return combine_datasets(tables), None, None, 'csv'

    data, metadata = load_wav_textgrid(workspace, wav_files, textgrid_files, ceiling_options)
    if data is not None and not data.empty and 'file' in data.columns:
        by_stem = {os.path.splitext(f['name'])[0]: set_labels[f['name']] for f in wav_files}
        data = data.copy()
        data['upload_set'] = data['file'].map(by_stem)
    if not tables:
        return data, None, metadata, 'wav_textgrid'

    if data is None or data.empty:
        raise UploadError('No vowels could be measured in the WAV/TextGrid files. Each TextGrid needs an interval '
                          'tier with phone- or vowel-level labels; delete these files to plot the tables alone.')
    data = remove_outliers_by_vowel(data)
    save_extracted_csv(workspace, data)
    return combine_datasets(tables + [('recordings', data)]), None, metadata, 'mixed'


COMPARE_MODES = ('auto', 'set', 'prefix', 'speaker', 'language', 'off')
COMPARE_TITLES = {'set': 'Upload sets', 'prefix': 'Speaker groups', 'speaker': 'Speakers', 'language': 'Language / group'}


def comparison_groups(data, workspace, mode):
    """
    Which groups of rows the plot should contrast.

    ``mode`` is one of COMPARE_MODES: 'set' compares the upload sets (files
    added later against the ones uploaded before), 'prefix' the letters at the
    start of the speaker ID (fv01, fv02 -> fv; mv01 -> mv), 'speaker' the
    speakers and 'language' the native_language column; 'auto' compares upload
    sets when there are at least two; 'off' never compares.
    Returns (data with a ``compare_group`` column, mode used) or (None, None)
    when there is nothing to compare.
    """
    mode = mode if mode in COMPARE_MODES else 'auto'
    if mode == 'off' or data is None or data.empty:
        return None, None

    def from_column(column, transform=None):
        if column not in data.columns:
            return None
        values = data[column].astype(str).where(data[column].notna())
        return transform(values) if transform else values

    if mode in ('auto', 'set'):
        mode = 'set'
        groups = from_column('upload_set')
        numbers = {label: number for number, label in workspace.file_sets().values()}
        rank = lambda g: g.map(lambda label: numbers.get(label, 0))
    elif mode == 'prefix':
        groups = from_column('speaker', lambda v: v.str.extract(r'^([^\W\d_]+)', expand=False).fillna(v))
        rank = None
    else:
        groups = from_column('speaker' if mode == 'speaker' else 'native_language')
        rank = None

    if groups is None or groups.nunique(dropna=True) < 2:
        return None, None
    data = data.assign(compare_group=groups)
    data = data[data['compare_group'].notna()]
    data = data.assign(_rank=rank(data['compare_group']) if rank else data['compare_group'])
    return data.sort_values('_rank', kind='stable').drop(columns='_rank'), mode


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def parse_ceiling_options(form):
    """
    Read the formant-ceiling options from the upload form.

    ``formant_ceiling`` is 'auto' (per-speaker optimisation), a number in Hz,
    or 'custom' with the value in ``custom_ceiling``. ``ceiling_criterion`` is
    'f3f4' (default), 'f1f2' or 'combined'. ``ceiling_scope`` is 'speaker'
    (default) or 'vowel' (extra ceiling per speaker x vowel).
    Returns (mode, fixed_ceiling_hz, criterion, scope).
    """
    raw = (form.get('formant_ceiling') or 'auto').strip().lower()
    criterion = (form.get('ceiling_criterion') or 'f3f4').strip().lower()
    if criterion not in ('f3f4', 'f1f2', 'combined'):
        criterion = 'f3f4'
    scope = (form.get('ceiling_scope') or 'speaker').strip().lower()
    if scope not in ('speaker', 'vowel'):
        scope = 'speaker'
    if raw == 'auto':
        return 'auto', 5500.0, criterion, scope
    if raw == 'custom':
        raw = (form.get('custom_ceiling') or '').strip()
    try:
        ceiling = float(raw)
    except ValueError:
        return 'auto', 5500.0, criterion, scope
    ceiling = min(max(ceiling, 3000.0), 8000.0)
    return 'fixed', ceiling, criterion, scope


def summarize_ceiling_info(metadata):
    """Compact per-speaker ceiling summary for the JSON response (no sweep curves)."""
    if not metadata or 'formant_ceiling' not in metadata:
        return None
    info = metadata['formant_ceiling']
    speakers = {}
    for speaker, r in (info.get('speakers') or {}).items():
        speakers[speaker] = {
            'ceiling': r.get('ceiling'),
            'criterion': r.get('criterion'),
            'score': r.get('score'),
            'n_tokens': r.get('n_tokens'),
            'files': r.get('files'),
            'note': r.get('note'),
            'vowels': {
                v: {k: vr.get(k) for k in ('ceiling', 'criterion', 'score', 'n_tokens', 'note')}
                for v, vr in (r.get('vowels') or {}).items()
            } or None,
        }
    return {
        'mode': info.get('mode'),
        'criterion': info.get('criterion'),
        'scope': info.get('scope'),
        'fixed_ceiling': info.get('fixed_ceiling'),
        'speakers': speakers,
    }


@app.route('/')
def index():
    return render_template('index.html', username=current_user.username)


SLIDE_DECKS = {'ko': 'vowelspace.html', 'en': 'vowelspace_en.html'}


@app.route('/slides')
@app.route('/slides/<lang>')
def slides(lang='ko'):
    """Tutorial slides about the tool (slides/vowelspace*.html), for logged-in users."""
    if lang not in SLIDE_DECKS:
        return 'No slides in this language.', 404
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'slides', SLIDE_DECKS[lang])
    if not os.path.isfile(path):
        return 'The slides are not available on this server.', 404
    return send_file(path, mimetype='text/html', conditional=True)


@app.route('/upload', methods=['POST'])
@with_workspace
def upload_file(workspace):
    """
    Draw a plot from the user's files.

    Files in the request are added to the stored set first; without files the
    stored set is re-used, so only the parameters need to be sent again.
    """
    try:
        visualization_type = request.form.get('viz_type', 'static')
        show_ellipses = request.form.get('show_ellipses', 'false') == 'true'
        show_points = request.form.get('show_points', 'true') == 'true'
        formant_scale = request.form.get('formant_scale', 'Hz')  # Get scale option
        limit_basic_vowels = request.form.get('limit_basic_vowels', 'false') == 'true'

        data, detection_info, metadata, data_source = load_user_data(
            workspace, parse_ceiling_options(request.form))

        if metadata:
            with open(workspace.cache_path('last_metadata.json'), 'w') as f:
                json.dump(metadata, f, indent=2)

        if data is None or data.empty:
            # Return a user-friendly 400 error instead of 500 for invalid/empty data
            if data_source == 'wav_textgrid':
                err_msg = 'No vowels could be measured. Each TextGrid needs an interval tier with phone- or vowel-level labels (ARPABET, IPA or romanized Korean); word-level tiers are not used.'
            else:
                err_msg = 'Data processing failed. Please include F1 and F2 columns or provide numeric columns in reasonable formant ranges (F1: 200–1000 Hz, F2: 800–3000 Hz).'
            # If we have detection info, include a hint
            if detection_info is not None:
                try:
                    detected_cols = detection_info.get('detected', {})
                    err_msg += f" Detected columns: {detected_cols}."
                except Exception:
                    pass
            return jsonify({'error': err_msg}), 400

        basic_filter_applied = False
        basic_filter_removed = 0
        if limit_basic_vowels and ('vowel' in data.columns or 'vowel_raw' in data.columns):
            before_count = len(data)
            filtered_data = filter_basic_vowels(data)
            basic_filter_applied = True
            basic_filter_removed = before_count - len(filtered_data)
            if filtered_data.empty:
                return jsonify({'error': 'No vowels matched the selected filter (IPA: ɑ, eɪ, i, oʊ, u; Korean IPA: a, e, i, o, u).'}), 400
            data = filtered_data
            if basic_filter_removed:
                print(f"Basic vowel filter applied: removed {basic_filter_removed} rows (kept {len(data)})")
        else:
            basic_filter_applied = False
        
        # Save extracted data as CSV for WAV/TextGrid processing
        if data_source == 'wav_textgrid':
            # Remove outliers: values beyond ±3 standard deviations per vowel
            data_cleaned = remove_outliers_by_vowel(data)
            
            save_extracted_csv(workspace, data_cleaned)
            
            # Log outlier removal stats
            original_count = len(data)
            cleaned_count = len(data_cleaned)
            removed_count = original_count - cleaned_count
            print(f"Outlier removal: {removed_count} points removed ({original_count} → {cleaned_count})")
            
            # Update data for visualization (use cleaned data)
            data = data_cleaned
        
        # Convert formant scale if needed
        if formant_scale != 'Hz':
            data = convert_formants(data, from_scale='Hz', to_scale=formant_scale,
                                    formant_cols=[c for c in ('F1', 'F2', 'F3', 'F4') if c in data.columns])
        
        # Create visualization with scale label
        scale_label = get_scale_label(formant_scale)
        
        compared, compare_mode = comparison_groups(data, workspace, request.form.get('compare_by', 'auto'))
        if compared is not None and visualization_type not in ('static', 'ellipse'):
            compared, compare_mode = None, None        # trajectories keep the per-vowel colours

        if compared is not None:
            plot_json = create_group_comparison_plot(
                compared, scale=scale_label, show_points=show_points,
                ellipses=(visualization_type == 'ellipse' or show_ellipses),
                group_title=COMPARE_TITLES[compare_mode])
        elif visualization_type == 'static':
            if show_ellipses:
                plot_json = create_vowel_space_with_ellipses(data, n_std=1.0, show_points=show_points, scale=scale_label)
            else:
                plot_json = create_static_vowel_space(data, scale=scale_label)
        elif visualization_type == 'dynamic':
            plot_json = create_dynamic_formant_trajectory(data, scale=scale_label)
        elif visualization_type == 'trajectory_time':
            plot_json = create_formant_time_trajectory(data, scale=scale_label)
            if plot_json is None:
                return jsonify({'error': 'Formant-over-time plot needs at least two time points per vowel production (a time column with several rows per vowel).'}), 400
        elif visualization_type == 'ellipse':
            plot_json = create_vowel_space_with_ellipses(data, n_std=1.0, show_points=show_points, scale=scale_label)
        else:
            plot_json = create_static_vowel_space(data, scale=scale_label)
        
        if plot_json is None:
            return jsonify({'error': 'Visualization creation failed.'}), 500
        
        return jsonify({
            'success': True,
            'plot': plot_json,
            'data_source': data_source,
            'stored_files': workspace.listing(),
            'comparison': ({'by': compare_mode, 'groups': list(dict.fromkeys(compared['compare_group']))}
                           if compared is not None else None),
            'data_summary': {
                'rows': len(data),
                'vowels': data['vowel'].unique().tolist() if 'vowel' in data.columns else [],
                'columns': data.columns.tolist(),
                'column_detection': detection_info if detection_info else None,
                'formant_ceiling': summarize_ceiling_info(metadata),
                'filters': {
                    'basic_vowels_only': basic_filter_applied,
                    'removed_rows': basic_filter_removed,
                    'core_vowel_sets': CORE_VOWEL_DISPLAY_INFO if basic_filter_applied else None
                }
            }
        })
    
    except UploadError as e:
        return jsonify({'error': e.message}), e.status

    except Exception as e:
        print(f"Error in upload: {str(e)}")  # Debug log
        print(traceback.format_exc())  # Full traceback

        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@app.route('/example')
def example_data():
    """Provide example data"""
    import pandas as pd
    import numpy as np
    
    # Example static data
    vowels = ['i', 'e', 'a', 'o', 'u']
    data = []
    for vowel in vowels:
        for _ in range(10):
            if vowel == 'i':
                f1, f2 = np.random.normal(300, 20), np.random.normal(2300, 100)
            elif vowel == 'e':
                f1, f2 = np.random.normal(450, 30), np.random.normal(2100, 100)
            elif vowel == 'a':
                f1, f2 = np.random.normal(700, 40), np.random.normal(1200, 100)
            elif vowel == 'o':
                f1, f2 = np.random.normal(500, 30), np.random.normal(900, 80)
            else:  # u
                f1, f2 = np.random.normal(350, 25), np.random.normal(800, 80)
            
            data.append({'vowel': vowel, 'F1': f1, 'F2': f2})
    
    df = pd.DataFrame(data)
    plot_json = create_static_vowel_space(df)
    
    return jsonify({
        'success': True,
        'plot': plot_json
    })


@app.route('/analyze', methods=['POST'])
@with_workspace
def analyze_data(workspace):
    """Statistical analysis of the user's stored (or newly sent) files"""
    try:
        formant_scale = request.form.get('formant_scale', 'Hz')  # Get scale option
        limit_basic_vowels = request.form.get('limit_basic_vowels', 'false') == 'true'

        data, detection_info, _metadata, data_source = load_user_data(
            workspace, parse_ceiling_options(request.form))

        if data is None or data.empty:
            return jsonify({'success': False, 'error': 'Failed to process data'}), 400

        if data_source == 'wav_textgrid':
            data = remove_outliers_by_vowel(data)

        basic_filter_applied = False
        basic_filter_removed = 0
        if limit_basic_vowels and ('vowel' in data.columns or 'vowel_raw' in data.columns):
            before_count = len(data)
            filtered_data = filter_basic_vowels(data)
            basic_filter_applied = True
            basic_filter_removed = before_count - len(filtered_data)
            if filtered_data.empty:
                return jsonify({'success': False, 'error': 'No vowels matched the selected filter (IPA: ɑ, eɪ, i, oʊ, u; Korean IPA: a, e, i, o, u).'}), 400
            data = filtered_data
            if basic_filter_removed:
                print(f"Basic vowel filter applied (analysis): removed {basic_filter_removed} rows (kept {len(data)})")
        
        # Limit speakers to 10 randomly if more than 10
        if 'speaker' in data.columns:
            unique_speakers = data['speaker'].unique()
            if len(unique_speakers) > 10:
                import random
                random.seed(42)  # For reproducibility
                selected_speakers = random.sample(list(unique_speakers), 10)
                data = data[data['speaker'].isin(selected_speakers)].copy()
                print(f"Limited to 10 random speakers from {len(unique_speakers)} total speakers")
        
        # Convert formant scale if needed
        if formant_scale != 'Hz':
            data = convert_formants(data, from_scale='Hz', to_scale=formant_scale,
                                    formant_cols=[c for c in ('F1', 'F2', 'F3', 'F4') if c in data.columns])
        
        # Perform comprehensive analysis
        analysis_results = perform_comprehensive_analysis(data)
        
        # Create visualizations with scale label
        scale_label = get_scale_label(formant_scale)
        plots = {}
        
        # PCA plot
        if 'pca_data' in analysis_results:
            plots['pca'] = create_pca_plot(analysis_results['pca_data'], analysis_results['pca'], scale=scale_label)
        
        # LDA plots
        if 'vowel' in data.columns and 'lda_data_vowel' in analysis_results:
            plots['lda_vowel'] = create_lda_plot(
                analysis_results['lda_data_vowel'], 
                analysis_results['lda']['vowel'],
                group_by='vowel',
                scale=scale_label
            )
        
        if 'speaker' in data.columns and 'lda_data_speaker' in analysis_results:
            plots['lda_speaker'] = create_lda_plot(
                analysis_results['lda_data_speaker'],
                analysis_results['lda']['speaker'],
                group_by='speaker',
                scale=scale_label
            )
        
        if 'native_language' in data.columns and 'lda_data_native_language' in analysis_results:
            plots['lda_language'] = create_lda_plot(
                analysis_results['lda_data_native_language'],
                analysis_results['lda']['native_language'],
                group_by='native_language',
                scale=scale_label
            )
        
        # Statistical plots - create for each available grouping variable
        grouping_vars = []
        if 'vowel' in data.columns:
            grouping_vars.append('vowel')
        if 'speaker' in data.columns:
            grouping_vars.append('speaker')
        if 'native_language' in data.columns:
            grouping_vars.append('native_language')
        
        for group_var in grouping_vars:
            # Box plot
            boxplot = create_boxplot(data, group_by=group_var, scale=scale_label)
            if boxplot:
                plots[f'boxplot_{group_var}'] = boxplot
            
            # Violin plot
            violin = create_violin_plot(data, group_by=group_var, scale=scale_label)
            if violin:
                plots[f'violin_{group_var}'] = violin
            
            # Histogram
            histogram = create_histogram(data, group_by=group_var, scale=scale_label)
            if histogram:
                plots[f'histogram_{group_var}'] = histogram
            
            # Mean comparison plot
            mean_plot = create_mean_comparison_plot(data, group_by=group_var, scale=scale_label)
            if mean_plot:
                plots[f'mean_comparison_{group_var}'] = mean_plot
            
            # Pairwise comparison plot
            if 'pairwise' in analysis_results and group_var in analysis_results['pairwise']:
                pairwise_plot = create_pairwise_comparison_plot(
                    analysis_results['pairwise'][group_var], 
                    scale=scale_label
                )
                if pairwise_plot:
                    plots[f'pairwise_{group_var}'] = pairwise_plot
        
        # Scatter matrix (not grouped)
        if grouping_vars:
            scatter_matrix = create_scatter_matrix(data, color_by=grouping_vars[0])
            if scatter_matrix:
                plots['scatter_matrix'] = scatter_matrix
        
        # Remove large data objects before sending
        if 'pca_data' in analysis_results:
            del analysis_results['pca_data']
        
        keys_to_remove = [k for k in analysis_results.keys() if k.startswith('lda_data_')]
        for key in keys_to_remove:
            del analysis_results[key]
        
        # Convert all numpy types to JSON serializable types
        analysis_results = convert_to_json_serializable(analysis_results)
        plots = convert_to_json_serializable(plots)
        
        return jsonify({
            'success': True,
            'analysis': analysis_results,
            'plots': plots,
            'column_detection': detection_info,
            'filters': {
                'basic_vowels_only': basic_filter_applied,
                'removed_rows': basic_filter_removed,
                'core_vowel_sets': CORE_VOWEL_DISPLAY_INFO if basic_filter_applied else None
            }
        })
    
    except UploadError as e:
        return jsonify({'success': False, 'error': e.message}), e.status

    except Exception as e:
        print(f"Error in analysis: {str(e)}")
        print(traceback.format_exc())

        return jsonify({'success': False, 'error': f'Analysis failed: {str(e)}'}), 500


@app.route('/download-examples')
def download_examples():
    """Download example CSV files as a ZIP archive"""
    try:
        # Create in-memory ZIP file
        memory_file = io.BytesIO()
        
        # Path to test folder
        test_folder = Path(__file__).parent / 'test'
        
        with ZipFile(memory_file, 'w') as zf:
            # Find all CSV files in test folder
            csv_files = list(test_folder.glob('*.csv'))
            
            if not csv_files:
                return jsonify({'error': 'No example CSV files found'}), 404
            
            # Add each CSV file to the ZIP
            for csv_file in csv_files:
                zf.write(csv_file, arcname=csv_file.name)
        
        # Seek to the beginning of the BytesIO object
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='vowelspace_examples.zip'
        )
    
    except Exception as e:
        print(f"Error in download-examples: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


@app.route('/files')
@with_workspace
def stored_files(workspace):
    """Names and sizes of the files the user currently has on the server"""
    return jsonify(workspace.listing())


@app.route('/delete-files', methods=['POST'])
@with_workspace
def delete_files(workspace):
    """
    Delete uploaded files and everything derived from them.

    With ``names`` in the form only those files are deleted (a WAV and its
    TextGrid always go together, because one is useless without the other);
    without ``names`` all files of the user are deleted.
    """
    names = [n for n in request.form.getlist('names') if n]
    if not names:
        workspace.delete()
        return jsonify({'success': True, 'stored_files': workspace.listing()})

    stored = workspace.files()
    wanted = {f['name'] for f in stored if f['name'] in names}
    paired_stems = {os.path.splitext(f['name'])[0] for f in stored
                    if f['name'] in wanted and f['ext'] in ('wav', 'textgrid')}
    wanted |= {f['name'] for f in stored
               if f['ext'] in ('wav', 'textgrid') and os.path.splitext(f['name'])[0] in paired_stems}
    removed = workspace.delete_files(wanted)
    return jsonify({'success': True, 'removed': removed, 'stored_files': workspace.listing()})


@app.route('/download-extracted-data')
@with_workspace
def download_extracted_data(workspace):
    """Download extracted formant data as CSV"""
    try:
        csv_path = workspace.cache_path('last_extracted_data.csv')
        
        if not os.path.exists(csv_path):
            return jsonify({'error': 'No extracted data available. Please upload and analyze WAV/TextGrid files first.'}), 404
        
        return send_file(
            csv_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name='extracted_vowel_formants.csv'
        )
    
    except Exception as e:
        print(f"Error in download-extracted-data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug, host='0.0.0.0', port=port)
