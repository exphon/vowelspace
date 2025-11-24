from flask import Flask, render_template, request, jsonify, send_file
import os
from werkzeug.utils import secure_filename
import json
import traceback
import numpy as np
import pandas as pd
from pathlib import Path
from zipfile import ZipFile
import io
from utils.data_processor import process_csv_xlsx, process_wav_textgrid
from utils.visualizer import (
    create_static_vowel_space, 
    create_dynamic_formant_trajectory,
    create_vowel_space_with_ellipses,
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


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size for WAV/TextGrid
app.config['ALLOWED_EXTENSIONS'] = {'wav', 'TextGrid', 'textgrid', 'csv', 'xlsx', 'xls', 'txt'}

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No file was uploaded.'}), 400
        
        files = request.files.getlist('files')
        visualization_type = request.form.get('viz_type', 'static')
        show_ellipses = request.form.get('show_ellipses', 'false') == 'true'
        show_points = request.form.get('show_points', 'true') == 'true'
        formant_scale = request.form.get('formant_scale', 'Hz')  # Get scale option
        
        if not files or files[0].filename == '':
            return jsonify({'error': 'Please select a file.'}), 400
        
        uploaded_files = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                uploaded_files.append({
                    'name': filename,
                    'path': filepath,
                    'ext': filename.rsplit('.', 1)[1].lower()
                })
        
        if not uploaded_files:
            return jsonify({'error': 'File format not allowed.'}), 400
        
        # Process files based on type
        data = None
        detection_info = None
        file_types = [f['ext'] for f in uploaded_files]
        
        if 'csv' in file_types or 'xlsx' in file_types or 'xls' in file_types or 'txt' in file_types:
            # Process spreadsheet data with auto-detection
            for f in uploaded_files:
                if f['ext'] in ['csv', 'xlsx', 'xls', 'txt']:
                    print(f"Processing file: {f['path']}")  # Debug log
                    result = process_csv_xlsx(f['path'], auto_detect=True)
                    
                    # Handle tuple return (df, detection_info)
                    if isinstance(result, tuple):
                        data, detection_info = result
                    else:
                        data = result
                    
                    print(f"Data shape: {data.shape if data is not None and not data.empty else 'Empty'}")  # Debug log
                    if detection_info:
                        print(f"Detected columns: {detection_info['detected']}")
                    break
        
        elif 'wav' in file_types:
            # Process WAV and TextGrid files
            wav_files = [f for f in uploaded_files if f['ext'] == 'wav']
            textgrid_files = [f for f in uploaded_files if f['ext'] in ['textgrid', 'TextGrid']]
            
            # Validate that WAV and TextGrid files are paired
            if len(wav_files) != len(textgrid_files):
                # Clean up uploaded files
                for f in uploaded_files:
                    if os.path.exists(f['path']):
                        os.remove(f['path'])
                return jsonify({
                    'error': f'Number of WAV files ({len(wav_files)}) does not match number of TextGrid files ({len(textgrid_files)}). Each WAV file must have a corresponding TextGrid file with the same basename.'
                }), 400
            
            # Check if basenames match
            wav_basenames = {os.path.splitext(os.path.basename(f['path']))[0] for f in wav_files}
            tg_basenames = {os.path.splitext(os.path.basename(f['path']))[0] for f in textgrid_files}
            
            if wav_basenames != tg_basenames:
                missing_tg = wav_basenames - tg_basenames
                missing_wav = tg_basenames - wav_basenames
                error_msg = 'WAV and TextGrid files do not form proper pairs. '
                if missing_tg:
                    error_msg += f'TextGrid files missing for: {", ".join(missing_tg)}. '
                if missing_wav:
                    error_msg += f'WAV files missing for: {", ".join(missing_wav)}.'
                
                # Clean up uploaded files
                for f in uploaded_files:
                    if os.path.exists(f['path']):
                        os.remove(f['path'])
                return jsonify({'error': error_msg}), 400
            
            print(f"Processing {len(wav_files)} WAV/TextGrid pairs")
            wav_paths = [f['path'] for f in wav_files]
            textgrid_paths = [f['path'] for f in textgrid_files]
            
            # Process with metadata extraction
            result = process_wav_textgrid(wav_paths, textgrid_paths)
            if isinstance(result, tuple):
                data, metadata = result
            else:
                data = result
                metadata = None
            
            # Store metadata for later download
            if metadata:
                import json
                metadata_path = os.path.join(app.config['UPLOAD_FOLDER'], 'last_metadata.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
        
        else:
            return jsonify({'error': 'Unsupported file combination.'}), 400
        
        if data is None or data.empty:
            # Return a user-friendly 400 error instead of 500 for invalid/empty data
            err_msg = 'Data processing failed. Please include F1 and F2 columns or provide numeric columns in reasonable formant ranges (F1: 200–1000 Hz, F2: 800–3000 Hz).'
            # If we have detection info, include a hint
            if detection_info is not None:
                try:
                    detected_cols = detection_info.get('detected', {})
                    err_msg += f" Detected columns: {detected_cols}."
                except Exception:
                    pass
            return jsonify({'error': err_msg}), 400
        
        # Save extracted data as CSV for WAV/TextGrid processing
        if 'wav' in file_types:
            # Remove outliers: values beyond ±3 standard deviations per vowel
            data_cleaned = remove_outliers_by_vowel(data)
            
            csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'last_extracted_data.csv')
            # Sort by vowel (alphabetically) and then by F1 (ascending)
            data_sorted = data_cleaned.sort_values(by=['vowel', 'F1'], ascending=[True, True])
            data_sorted.to_csv(csv_path, index=False)
            
            # Log outlier removal stats
            original_count = len(data)
            cleaned_count = len(data_cleaned)
            removed_count = original_count - cleaned_count
            print(f"Outlier removal: {removed_count} points removed ({original_count} → {cleaned_count})")
            print(f"Extracted data saved to {csv_path} (sorted by vowel and F1)")
            
            # Update data for visualization (use cleaned data)
            data = data_cleaned
        
        # Convert formant scale if needed
        if formant_scale != 'Hz':
            data = convert_formants(data, from_scale='Hz', to_scale=formant_scale)
        
        # Create visualization with scale label
        scale_label = get_scale_label(formant_scale)
        
        if visualization_type == 'static':
            if show_ellipses:
                plot_json = create_vowel_space_with_ellipses(data, confidence_level=0.95, show_points=show_points, scale=scale_label)
            else:
                plot_json = create_static_vowel_space(data, scale=scale_label)
        elif visualization_type == 'dynamic':
            plot_json = create_dynamic_formant_trajectory(data, scale=scale_label)
        elif visualization_type == 'ellipse':
            plot_json = create_vowel_space_with_ellipses(data, confidence_level=0.95, show_points=show_points, scale=scale_label)
        else:
            plot_json = create_static_vowel_space(data, scale=scale_label)
        
        if plot_json is None:
            return jsonify({'error': 'Visualization creation failed.'}), 500
        
        # Clean up uploaded files
        for f in uploaded_files:
            if os.path.exists(f['path']):
                os.remove(f['path'])
        
        # Determine data source type
        data_source = 'wav_textgrid' if 'wav' in file_types else 'csv'
        
        return jsonify({
            'success': True,
            'plot': plot_json,
            'data_source': data_source,
            'data_summary': {
                'rows': len(data),
                'vowels': data['vowel'].unique().tolist() if 'vowel' in data.columns else [],
                'columns': data.columns.tolist(),
                'column_detection': detection_info if detection_info else None
            }
        })
    
    except Exception as e:
        print(f"Error in upload: {str(e)}")  # Debug log
        print(traceback.format_exc())  # Full traceback
        
        # Clean up uploaded files on error
        try:
            for f in uploaded_files:
                if os.path.exists(f['path']):
                    os.remove(f['path'])
        except:
            pass
        
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
def analyze_data():
    """Statistical analysis endpoint"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        files = request.files.getlist('files')
        formant_scale = request.form.get('formant_scale', 'Hz')  # Get scale option
        
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        uploaded_files = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                uploaded_files.append({
                    'name': filename,
                    'path': filepath,
                    'ext': filename.rsplit('.', 1)[1].lower()
                })
        
        if not uploaded_files:
            return jsonify({'success': False, 'error': 'Invalid file format'}), 400
        
        # Process files
        data = None
        detection_info = None
        file_types = [f['ext'] for f in uploaded_files]
        
        if 'csv' in file_types or 'xlsx' in file_types or 'xls' in file_types or 'txt' in file_types:
            for f in uploaded_files:
                if f['ext'] in ['csv', 'xlsx', 'xls', 'txt']:
                    result = process_csv_xlsx(f['path'], auto_detect=True)
                    
                    if isinstance(result, tuple):
                        data, detection_info = result
                    else:
                        data = result
                    break
        
        if data is None or data.empty:
            return jsonify({'success': False, 'error': 'Failed to process data'}), 500
        
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
            data = convert_formants(data, from_scale='Hz', to_scale=formant_scale)
        
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
        
        # Clean up uploaded files
        for f in uploaded_files:
            if os.path.exists(f['path']):
                os.remove(f['path'])
        
        return jsonify({
            'success': True,
            'analysis': analysis_results,
            'plots': plots,
            'column_detection': detection_info
        })
    
    except Exception as e:
        print(f"Error in analysis: {str(e)}")
        print(traceback.format_exc())
        
        # Clean up on error
        try:
            for f in uploaded_files:
                if os.path.exists(f['path']):
                    os.remove(f['path'])
        except:
            pass
        
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


@app.route('/download-extracted-data')
def download_extracted_data():
    """Download extracted formant data as CSV"""
    try:
        csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'last_extracted_data.csv')
        
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
    app.run(debug=True, host='0.0.0.0', port=5000)
