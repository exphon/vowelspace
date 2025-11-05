from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
import json
import traceback
import numpy as np
from utils.data_processor import process_csv_xlsx, process_wav_textgrid
from utils.visualizer import (
    create_static_vowel_space, 
    create_dynamic_formant_trajectory,
    create_vowel_space_with_ellipses,
    create_pca_plot,
    create_lda_plot
)
from utils.statistics import perform_comprehensive_analysis


def convert_to_json_serializable(obj):
    """Convert numpy types to native Python types for JSON serialization"""
    if isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    else:
        return obj

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'wav', 'TextGrid', 'csv', 'xlsx', 'xls', 'txt'}

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
            return jsonify({'error': '파일이 업로드되지 않았습니다.'}), 400
        
        files = request.files.getlist('files')
        visualization_type = request.form.get('viz_type', 'static')
        show_ellipses = request.form.get('show_ellipses', 'false') == 'true'
        show_points = request.form.get('show_points', 'true') == 'true'
        
        if not files or files[0].filename == '':
            return jsonify({'error': '파일을 선택해주세요.'}), 400
        
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
            return jsonify({'error': '허용되지 않은 파일 형식입니다.'}), 400
        
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
            wav_files = [f['path'] for f in uploaded_files if f['ext'] == 'wav']
            textgrid_files = [f['path'] for f in uploaded_files if f['ext'] == 'textgrid']
            print(f"Processing WAV files: {wav_files}")  # Debug log
            data = process_wav_textgrid(wav_files, textgrid_files)
        
        else:
            return jsonify({'error': '지원되지 않는 파일 조합입니다.'}), 400
        
        if data is None or data.empty:
            return jsonify({'error': '데이터 처리에 실패했습니다. 파일 형식을 확인해주세요.'}), 500
        
        # Create visualization
        if visualization_type == 'static':
            if show_ellipses:
                plot_json = create_vowel_space_with_ellipses(data, confidence_level=0.95, show_points=show_points)
            else:
                plot_json = create_static_vowel_space(data)
        elif visualization_type == 'dynamic':
            plot_json = create_dynamic_formant_trajectory(data)
        elif visualization_type == 'ellipse':
            plot_json = create_vowel_space_with_ellipses(data, confidence_level=0.95, show_points=show_points)
        else:
            plot_json = create_static_vowel_space(data)
        
        if plot_json is None:
            return jsonify({'error': '시각화 생성에 실패했습니다.'}), 500
        
        # Clean up uploaded files
        for f in uploaded_files:
            if os.path.exists(f['path']):
                os.remove(f['path'])
        
        return jsonify({
            'success': True,
            'plot': plot_json,
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
        
        return jsonify({'error': f'오류가 발생했습니다: {str(e)}'}), 500


@app.route('/example')
def example_data():
    """예제 데이터 제공"""
    import pandas as pd
    import numpy as np
    
    # 예제 정적 데이터
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
    """통계 분석 엔드포인트"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        files = request.files.getlist('files')
        
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
        
        # Perform comprehensive analysis
        analysis_results = perform_comprehensive_analysis(data)
        
        # Create visualizations
        plots = {}
        
        # PCA plot
        if 'pca_data' in analysis_results:
            plots['pca'] = create_pca_plot(analysis_results['pca_data'], analysis_results['pca'])
        
        # LDA plots
        if 'vowel' in data.columns and 'lda_data_vowel' in analysis_results:
            plots['lda_vowel'] = create_lda_plot(
                analysis_results['lda_data_vowel'], 
                analysis_results['lda']['vowel'],
                group_by='vowel'
            )
        
        if 'speaker' in data.columns and 'lda_data_speaker' in analysis_results:
            plots['lda_speaker'] = create_lda_plot(
                analysis_results['lda_data_speaker'],
                analysis_results['lda']['speaker'],
                group_by='speaker'
            )
        
        if 'native_language' in data.columns and 'lda_data_native_language' in analysis_results:
            plots['lda_language'] = create_lda_plot(
                analysis_results['lda_data_native_language'],
                analysis_results['lda']['native_language'],
                group_by='native_language'
            )
        
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
