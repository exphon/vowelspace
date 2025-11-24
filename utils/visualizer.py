"""
Visualization utilities for creating vowel space and formant trajectory plots
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import json
from scipy import stats

# Custom color palette - dark colors without yellow
CUSTOM_COLORS = [
    '#e41a1c',  # Red
    '#377eb8',  # Blue
    '#4daf4a',  # Green
    '#984ea3',  # Purple
    '#ff7f00',  # Orange
    '#a65628',  # Brown
    '#f781bf',  # Pink
    '#999999',  # Gray
    '#1b9e77',  # Teal
    '#d95f02',  # Dark Orange
    '#7570b3',  # Dark Purple
    '#e7298a',  # Magenta
]


def calculate_ellipse(x, y, n_std=2.0, n_points=100):
    """
    Calculate confidence ellipse for 2D data
    
    Args:
        x, y: Data points
        n_std: Number of standard deviations (2.0 for ~95% confidence)
        n_points: Number of points to draw the ellipse
    
    Returns:
        x_ellipse, y_ellipse: Coordinates of the ellipse
    """
    if len(x) < 3:  # Need at least 3 points for ellipse
        return None, None
    
    # Calculate covariance matrix
    cov = np.cov(x, y)
    
    # Calculate eigenvalues and eigenvectors
    eigenvalues, eigenvectors = np.linalg.eig(cov)
    
    # Calculate angle of ellipse
    angle = np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0])
    
    # Calculate width and height
    width = 2 * n_std * np.sqrt(eigenvalues[0])
    height = 2 * n_std * np.sqrt(eigenvalues[1])
    
    # Generate ellipse points
    t = np.linspace(0, 2 * np.pi, n_points)
    ellipse_x = width * np.cos(t)
    ellipse_y = height * np.sin(t)
    
    # Rotate ellipse
    rotation_matrix = np.array([
        [np.cos(angle), -np.sin(angle)],
        [np.sin(angle), np.cos(angle)]
    ])
    
    rotated = rotation_matrix @ np.array([ellipse_x, ellipse_y])
    
    # Translate to center
    center_x = np.mean(x)
    center_y = np.mean(y)
    
    x_ellipse = rotated[0, :] + center_x
    y_ellipse = rotated[1, :] + center_y
    
    return x_ellipse, y_ellipse


def create_static_vowel_space(df, scale='Hz'):
    """
    Create an interactive static vowel space plot (F1 vs F2)
    Supports filtering by vowel, speaker, and native_language
    Traditionally, F1 is on Y-axis (inverted) and F2 is on X-axis (inverted)
    
    Args:
        df: DataFrame with F1, F2 columns
        scale: Frequency scale label ('Hz', 'Bark', 'ERB', 'Mel')
    """
    if df is None or df.empty:
        print("Error: Empty dataframe in create_static_vowel_space")
        return None
    
    try:
        fig = go.Figure()
        
        # Determine grouping strategy based on available columns
        has_vowel = 'vowel' in df.columns
        has_speaker = 'speaker' in df.columns
        has_language = 'native_language' in df.columns
        
        # Color palette
        colors = CUSTOM_COLORS
        
        if has_vowel and has_speaker and has_language:
            # 3-level grouping: Language > Speaker > Vowel
            color_idx = 0
            
            for lang in sorted(df['native_language'].unique()):
                lang_data = df[df['native_language'] == lang]
                
                for speaker in sorted(lang_data['speaker'].unique()):
                    speaker_data = lang_data[lang_data['speaker'] == speaker]
                    
                    for vowel in sorted(speaker_data['vowel'].unique()):
                        vowel_data = speaker_data[speaker_data['vowel'] == vowel]
                        
                        hover_text = [
                            f"<b>{vowel}</b><br>" +
                            f"Speaker: {speaker}<br>" +
                            f"Language: {lang}<br>" +
                            f"F1: {f1:.0f} Hz<br>" +
                            f"F2: {f2:.0f} Hz"
                            for f1, f2 in zip(vowel_data['F1'], vowel_data['F2'])
                        ]
                        
                        fig.add_trace(go.Scatter(
                            x=vowel_data['F2'],
                            y=vowel_data['F1'],
                            mode='markers',
                            name=vowel,
                            legendgroup=f"{lang}_{speaker}",
                            legendgrouptitle=dict(text=f"<b>{lang}</b> - {speaker}"),
                            marker=dict(
                                size=10,
                                color=colors[color_idx % len(colors)],
                                opacity=0.7,
                                line=dict(width=1, color='white')
                            ),
                            text=hover_text,
                            hoverinfo='text'
                        ))
                        color_idx += 1
                        
        elif has_vowel and has_speaker:
            # 2-level grouping: Speaker > Vowel
            color_idx = 0
            
            for speaker in sorted(df['speaker'].unique()):
                speaker_data = df[df['speaker'] == speaker]
                
                for vowel in sorted(speaker_data['vowel'].unique()):
                    vowel_data = speaker_data[speaker_data['vowel'] == vowel]
                    
                    hover_text = [
                        f"<b>{vowel}</b><br>" +
                        f"Speaker: {speaker}<br>" +
                        f"F1: {f1:.0f} Hz<br>" +
                        f"F2: {f2:.0f} Hz"
                        for f1, f2 in zip(vowel_data['F1'], vowel_data['F2'])
                    ]
                    
                    fig.add_trace(go.Scatter(
                        x=vowel_data['F2'],
                        y=vowel_data['F1'],
                        mode='markers',
                        name=vowel,
                        legendgroup=speaker,
                        legendgrouptitle=dict(text=f"<b>{speaker}</b>"),
                        marker=dict(
                            size=10,
                            color=colors[color_idx % len(colors)],
                            opacity=0.7,
                            line=dict(width=1, color='white')
                        ),
                        text=hover_text,
                        hoverinfo='text'
                    ))
                    color_idx += 1
                    
        elif has_vowel and has_language:
            # 2-level grouping: Language > Vowel
            color_idx = 0
            
            for lang in sorted(df['native_language'].unique()):
                lang_data = df[df['native_language'] == lang]
                
                for vowel in sorted(lang_data['vowel'].unique()):
                    vowel_data = lang_data[lang_data['vowel'] == vowel]
                    
                    hover_text = [
                        f"<b>{vowel}</b><br>" +
                        f"Language: {lang}<br>" +
                        f"F1: {f1:.0f} Hz<br>" +
                        f"F2: {f2:.0f} Hz"
                        for f1, f2 in zip(vowel_data['F1'], vowel_data['F2'])
                    ]
                    
                    fig.add_trace(go.Scatter(
                        x=vowel_data['F2'],
                        y=vowel_data['F1'],
                        mode='markers',
                        name=vowel,
                        legendgroup=lang,
                        legendgrouptitle=dict(text=f"<b>{lang}</b>"),
                        marker=dict(
                            size=10,
                            color=colors[color_idx % len(colors)],
                            opacity=0.7,
                            line=dict(width=1, color='white')
                        ),
                        text=hover_text,
                        hoverinfo='text'
                    ))
                    color_idx += 1
                    
        elif has_vowel:
            # Single-level grouping: Vowel only
            for idx, vowel in enumerate(sorted(df['vowel'].unique())):
                vowel_data = df[df['vowel'] == vowel]
                
                hover_text = [
                    f"<b>{vowel}</b><br>" +
                    f"F1: {f1:.0f} Hz<br>" +
                    f"F2: {f2:.0f} Hz"
                    for f1, f2 in zip(vowel_data['F1'], vowel_data['F2'])
                ]
                
                fig.add_trace(go.Scatter(
                    x=vowel_data['F2'],
                    y=vowel_data['F1'],
                    mode='markers',
                    name=vowel,
                    marker=dict(
                        size=10,
                        color=colors[idx % len(colors)],
                        opacity=0.7,
                        line=dict(width=1, color='white')
                    ),
                    text=hover_text,
                    hoverinfo='text'
                ))
        else:
            # No grouping - simple scatter plot
            hover_text = [
                f"F1: {f1:.0f} Hz<br>F2: {f2:.0f} Hz"
                for f1, f2 in zip(df['F1'], df['F2'])
            ]
            
            fig.add_trace(go.Scatter(
                x=df['F2'],
                y=df['F1'],
                mode='markers',
                marker=dict(size=10, color='blue', opacity=0.6),
                text=hover_text,
                hoverinfo='text'
            ))
        
        # Invert axes (traditional vowel space representation)
        fig.update_xaxes(
            autorange='reversed',
            title=f'F2 ({scale})',
            showgrid=True,
            gridcolor='lightgray'
        )
        fig.update_yaxes(
            autorange='reversed',
            title=f'F1 ({scale})',
            showgrid=True,
            gridcolor='lightgray'
        )
        
        # Update layout with interactive legend
        fig.update_layout(
            title=f'Interactive Vowel Space (F1 vs F2) - {scale}<br><sub>Click legend items to show/hide • Double-click to isolate</sub>',
            width=1000,
            height=700,
            plot_bgcolor='white',
            hovermode='closest',
            font=dict(size=12),
            legend=dict(
                title=dict(
                    text='<b>Groups</b><br><sub>(click to toggle)</sub>',
                    font=dict(size=14)
                ),
                orientation='v',
                yanchor='top',
                y=1,
                xanchor='left',
                x=1.02,
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor='gray',
                borderwidth=1,
                itemclick='toggle',
                itemdoubleclick='toggleothers',
                tracegroupgap=10
            )
        )
        
        return json.loads(fig.to_json())
    
    except Exception as e:
        print(f"Error creating static vowel space: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def create_dynamic_formant_trajectory(df, scale='Hz'):
    """
    Create an interactive dynamic formant trajectory plot
    Shows how formants change over time with grouping by vowel, speaker, and language
    
    Args:
        df: DataFrame with formant data
        scale: Frequency scale label ('Hz', 'Bark', 'ERB', 'Mel')
    """
    if df.empty:
        return None
    
    # Check if time information is available
    if 'time' not in df.columns:
        # If no time column, create static plot with sequence numbers
        if 'vowel' not in df.columns:
            return create_static_vowel_space(df)
        
        # Group by vowel and add sequence number
        df = df.copy()
        df['sequence'] = df.groupby('vowel').cumcount()
        time_col = 'sequence'
        time_label = 'Sequence'
    else:
        time_col = 'time'
        time_label = 'Time (s)'
    
    fig = go.Figure()
    
    # Determine grouping strategy
    has_vowel = 'vowel' in df.columns
    has_speaker = 'speaker' in df.columns
    has_language = 'native_language' in df.columns
    
    colors = CUSTOM_COLORS
    color_idx = 0
    
    if has_vowel and has_speaker and has_language:
        # 3-level grouping with trajectories
        for lang in sorted(df['native_language'].unique()):
            lang_data = df[df['native_language'] == lang]
            
            for speaker in sorted(lang_data['speaker'].unique()):
                speaker_data = lang_data[lang_data['speaker'] == speaker]
                
                for vowel in sorted(speaker_data['vowel'].unique()):
                    vowel_data = speaker_data[speaker_data['vowel'] == vowel].sort_values(time_col)
                    
                    if len(vowel_data) > 1:
                        hover_text = [
                            f"<b>{vowel}</b><br>" +
                            f"Speaker: {speaker}<br>" +
                            f"Language: {lang}<br>" +
                            f"F1: {f1:.0f} Hz<br>" +
                            f"F2: {f2:.0f} Hz<br>" +
                            f"{time_label}: {t:.3f}"
                            for f1, f2, t in zip(vowel_data['F1'], vowel_data['F2'], vowel_data[time_col])
                        ]
                        
                        fig.add_trace(go.Scatter(
                            x=vowel_data['F2'],
                            y=vowel_data['F1'],
                            mode='lines+markers',
                            name=vowel,
                            legendgroup=f"{lang}_{speaker}",
                            legendgrouptitle=dict(text=f"<b>{lang}</b> - {speaker}"),
                            line=dict(color=colors[color_idx % len(colors)], width=2),
                            marker=dict(size=8, opacity=0.7),
                            text=hover_text,
                            hoverinfo='text'
                        ))
                        color_idx += 1
                        
    elif has_vowel and has_speaker:
        # 2-level grouping
        for speaker in sorted(df['speaker'].unique()):
            speaker_data = df[df['speaker'] == speaker]
            
            for vowel in sorted(speaker_data['vowel'].unique()):
                vowel_data = speaker_data[speaker_data['vowel'] == vowel].sort_values(time_col)
                
                if len(vowel_data) > 1:
                    hover_text = [
                        f"<b>{vowel}</b><br>" +
                        f"Speaker: {speaker}<br>" +
                        f"F1: {f1:.0f} Hz<br>" +
                        f"F2: {f2:.0f} Hz<br>" +
                        f"{time_label}: {t:.3f}"
                        for f1, f2, t in zip(vowel_data['F1'], vowel_data['F2'], vowel_data[time_col])
                    ]
                    
                    fig.add_trace(go.Scatter(
                        x=vowel_data['F2'],
                        y=vowel_data['F1'],
                        mode='lines+markers',
                        name=vowel,
                        legendgroup=speaker,
                        legendgrouptitle=dict(text=f"<b>{speaker}</b>"),
                        line=dict(color=colors[color_idx % len(colors)], width=2),
                        marker=dict(size=8, opacity=0.7),
                        text=hover_text,
                        hoverinfo='text'
                    ))
                    color_idx += 1
                    
    elif has_vowel:
        # Single-level grouping
        for idx, vowel in enumerate(sorted(df['vowel'].unique())):
            vowel_data = df[df['vowel'] == vowel].sort_values(time_col)
            
            if len(vowel_data) > 1:
                hover_text = [
                    f"<b>{vowel}</b><br>" +
                    f"F1: {f1:.0f} Hz<br>" +
                    f"F2: {f2:.0f} Hz<br>" +
                    f"{time_label}: {t:.3f}"
                    for f1, f2, t in zip(vowel_data['F1'], vowel_data['F2'], vowel_data[time_col])
                ]
                
                fig.add_trace(go.Scatter(
                    x=vowel_data['F2'],
                    y=vowel_data['F1'],
                    mode='lines+markers',
                    name=vowel,
                    line=dict(color=colors[idx % len(colors)], width=2),
                    marker=dict(size=8, opacity=0.7),
                    text=hover_text,
                    hoverinfo='text'
                ))
    else:
        # No grouping - single trajectory
        df_sorted = df.sort_values(time_col)
        
        hover_text = [
            f"F1: {f1:.0f} Hz<br>F2: {f2:.0f} Hz<br>{time_label}: {t:.3f}"
            for f1, f2, t in zip(df_sorted['F1'], df_sorted['F2'], df_sorted[time_col])
        ]
        
        fig.add_trace(go.Scatter(
            x=df_sorted['F2'],
            y=df_sorted['F1'],
            mode='lines+markers',
            line=dict(color='blue', width=2),
            marker=dict(size=8, opacity=0.7),
            text=hover_text,
            hoverinfo='text'
        ))
    
    # Invert axes (traditional vowel space representation)
    fig.update_xaxes(
        autorange='reversed',
        title=f'F2 ({scale})',
        showgrid=True,
        gridcolor='lightgray'
    )
    fig.update_yaxes(
        autorange='reversed',
        title=f'F1 ({scale})',
        showgrid=True,
        gridcolor='lightgray'
    )
    
    # Update layout
    fig.update_layout(
        title=f'Interactive Formant Trajectory - {scale}<br><sub>Click legend items to show/hide • Double-click to isolate</sub>',
        width=1000,
        height=700,
        plot_bgcolor='white',
        hovermode='closest',
        font=dict(size=12),
        legend=dict(
            title=dict(
                text='<b>Groups</b><br><sub>(click to toggle)</sub>',
                font=dict(size=14)
            ),
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor='gray',
            borderwidth=1,
            itemclick='toggle',
            itemdoubleclick='toggleothers',
            tracegroupgap=10
        )
    )
    
    return json.loads(fig.to_json())


def create_formant_over_time(df):
    """
    Create a plot showing F1 and F2 values over time
    Useful for analyzing formant changes
    """
    if df.empty or 'time' not in df.columns:
        return None
    
    fig = go.Figure()
    
    # Plot F1 over time
    if 'vowel' in df.columns:
        for vowel in df['vowel'].unique():
            vowel_data = df[df['vowel'] == vowel].sort_values('time')
            
            fig.add_trace(go.Scatter(
                x=vowel_data['time'],
                y=vowel_data['F1'],
                mode='lines+markers',
                name=f'{vowel} - F1',
                line=dict(dash='solid')
            ))
            
            fig.add_trace(go.Scatter(
                x=vowel_data['time'],
                y=vowel_data['F2'],
                mode='lines+markers',
                name=f'{vowel} - F2',
                line=dict(dash='dash')
            ))
    else:
        df_sorted = df.sort_values('time')
        
        fig.add_trace(go.Scatter(
            x=df_sorted['time'],
            y=df_sorted['F1'],
            mode='lines+markers',
            name='F1',
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=df_sorted['time'],
            y=df_sorted['F2'],
            mode='lines+markers',
            name='F2',
            line=dict(color='red')
        ))
    
    fig.update_layout(
        title='Formant Values Over Time',
        xaxis_title='Time (s)',
        yaxis_title='Frequency (Hz)',
        width=900,
        height=500,
        hovermode='x unified'
    )
    
    return json.loads(fig.to_json())


def create_vowel_space_with_ellipses(df, confidence=0.95, show_points=True):
    """
    Create vowel space plot with confidence ellipses
    
    Args:
        df: DataFrame with F1, F2, vowel (and optionally speaker, native_language)
        confidence: Confidence level for ellipse (0.95 for 95% confidence interval)
        show_points: Whether to show individual data points
    
    Returns:
        Plotly figure JSON
    """
    if df is None or df.empty:
        print("Error: Empty dataframe")
        return None
    
    # Convert confidence to number of standard deviations
    # 95% ≈ 2 std, 99% ≈ 2.58 std
    if confidence >= 0.99:
        n_std = 1.0
    elif confidence >= 0.95:
        n_std = 1.0
    else:
        n_std = 1.0
    
    try:
        fig = go.Figure()
        
        has_vowel = 'vowel' in df.columns
        has_speaker = 'speaker' in df.columns
        has_language = 'native_language' in df.columns
        
        colors = CUSTOM_COLORS
        
        if has_vowel and has_speaker and has_language:
            # Group by Language > Speaker > Vowel with ellipses
            color_idx = 0
            
            for lang in sorted(df['native_language'].unique()):
                lang_data = df[df['native_language'] == lang]
                
                for speaker in sorted(lang_data['speaker'].unique()):
                    speaker_data = lang_data[lang_data['speaker'] == speaker]
                    
                    for vowel in sorted(speaker_data['vowel'].unique()):
                        vowel_data = speaker_data[speaker_data['vowel'] == vowel]
                        color = colors[color_idx % len(colors)]
                        
                        # Show individual points if requested
                        if show_points:
                            hover_text = [
                                f"<b>{vowel}</b><br>" +
                                f"Speaker: {speaker}<br>" +
                                f"Language: {lang}<br>" +
                                f"F1: {f1:.0f} Hz<br>" +
                                f"F2: {f2:.0f} Hz"
                                for f1, f2 in zip(vowel_data['F1'], vowel_data['F2'])
                            ]
                            
                            fig.add_trace(go.Scatter(
                                x=vowel_data['F2'],
                                y=vowel_data['F1'],
                                mode='markers',
                                name=f"{lang} | {speaker} | {vowel}",
                                legendgroup=f"{lang}_{speaker}_{vowel}",
                                marker=dict(
                                    size=6,
                                    color=color,
                                    opacity=0.4,
                                    line=dict(width=0.5, color='white')
                                ),
                                text=hover_text,
                                hoverinfo='text',
                                showlegend=True
                            ))
                        
                        # Add ellipse
                        if len(vowel_data) >= 3:
                            x_ellipse, y_ellipse = calculate_ellipse(
                                vowel_data['F2'].values, 
                                vowel_data['F1'].values, 
                                n_std=n_std
                            )
                            
                            if x_ellipse is not None:
                                fig.add_trace(go.Scatter(
                                    x=x_ellipse,
                                    y=y_ellipse,
                                    mode='lines',
                                    name=f"{lang} | {speaker} | {vowel} (ellipse)",
                                    legendgroup=f"{lang}_{speaker}_{vowel}",
                                    line=dict(color=color, width=2),
                                    fill='toself',
                                    fillcolor=color,
                                    opacity=0.2,
                                    hoverinfo='skip',
                                    showlegend=False
                                ))
                                
                                # Add mean point with label
                                mean_f1 = vowel_data['F1'].mean()
                                mean_f2 = vowel_data['F2'].mean()
                                
                                fig.add_trace(go.Scatter(
                                    x=[mean_f2],
                                    y=[mean_f1],
                                    mode='markers+text',
                                    name=f"{lang} | {speaker} | {vowel} (mean)",
                                    legendgroup=f"{lang}_{speaker}_{vowel}",
                                    marker=dict(
                                        size=12,
                                        color=color,
                                        symbol='circle',
                                        line=dict(width=2, color='white')
                                    ),
                                    text=vowel,
                                    textposition='middle center',
                                    textfont=dict(color='white', size=10, family='Arial Black'),
                                    hovertext=f"<b>{vowel}</b><br>Speaker: {speaker}<br>Language: {lang}<br>" +
                                             f"Mean F1: {mean_f1:.0f} Hz<br>Mean F2: {mean_f2:.0f} Hz<br>" +
                                             f"N = {len(vowel_data)}",
                                    hoverinfo='text',
                                    showlegend=False
                                ))
                        
                        color_idx += 1
                        
        elif has_vowel and has_speaker:
            # Group by Speaker > Vowel
            color_idx = 0
            
            for speaker in sorted(df['speaker'].unique()):
                speaker_data = df[df['speaker'] == speaker]
                
                for vowel in sorted(speaker_data['vowel'].unique()):
                    vowel_data = speaker_data[speaker_data['vowel'] == vowel]
                    color = colors[color_idx % len(colors)]
                    
                    if show_points:
                        hover_text = [
                            f"<b>{vowel}</b><br>Speaker: {speaker}<br>" +
                            f"F1: {f1:.0f} Hz<br>F2: {f2:.0f} Hz"
                            for f1, f2 in zip(vowel_data['F1'], vowel_data['F2'])
                        ]
                        
                        fig.add_trace(go.Scatter(
                            x=vowel_data['F2'],
                            y=vowel_data['F1'],
                            mode='markers',
                            name=f"{speaker} | {vowel}",
                            legendgroup=f"{speaker}_{vowel}",
                            marker=dict(size=6, color=color, opacity=0.4),
                            text=hover_text,
                            hoverinfo='text'
                        ))
                    
                    # Add ellipse
                    if len(vowel_data) >= 3:
                        x_ellipse, y_ellipse = calculate_ellipse(
                            vowel_data['F2'].values, 
                            vowel_data['F1'].values, 
                            n_std=n_std
                        )
                        
                        if x_ellipse is not None:
                            fig.add_trace(go.Scatter(
                                x=x_ellipse,
                                y=y_ellipse,
                                mode='lines',
                                legendgroup=f"{speaker}_{vowel}",
                                line=dict(color=color, width=2),
                                fill='toself',
                                fillcolor=color,
                                opacity=0.2,
                                hoverinfo='skip',
                                showlegend=False
                            ))
                            
                            # Mean point
                            mean_f1 = vowel_data['F1'].mean()
                            mean_f2 = vowel_data['F2'].mean()
                            
                            fig.add_trace(go.Scatter(
                                x=[mean_f2],
                                y=[mean_f1],
                                mode='markers+text',
                                legendgroup=f"{speaker}_{vowel}",
                                marker=dict(size=12, color=color, symbol='circle',
                                          line=dict(width=2, color='white')),
                                text=vowel,
                                textposition='middle center',
                                textfont=dict(color='white', size=10, family='Arial Black'),
                                hovertext=f"<b>{vowel}</b><br>Speaker: {speaker}<br>" +
                                         f"Mean F1: {mean_f1:.0f} Hz<br>Mean F2: {mean_f2:.0f} Hz<br>" +
                                         f"N = {len(vowel_data)}",
                                hoverinfo='text',
                                showlegend=False
                            ))
                    
                    color_idx += 1
                    
        elif has_vowel:
            # Group by Vowel only
            for idx, vowel in enumerate(sorted(df['vowel'].unique())):
                vowel_data = df[df['vowel'] == vowel]
                color = colors[idx % len(colors)]
                
                if show_points:
                    hover_text = [
                        f"<b>{vowel}</b><br>F1: {f1:.0f} Hz<br>F2: {f2:.0f} Hz"
                        for f1, f2 in zip(vowel_data['F1'], vowel_data['F2'])
                    ]
                    
                    fig.add_trace(go.Scatter(
                        x=vowel_data['F2'],
                        y=vowel_data['F1'],
                        mode='markers',
                        name=vowel,
                        legendgroup=vowel,
                        marker=dict(size=6, color=color, opacity=0.4),
                        text=hover_text,
                        hoverinfo='text'
                    ))
                
                # Add ellipse
                if len(vowel_data) >= 3:
                    x_ellipse, y_ellipse = calculate_ellipse(
                        vowel_data['F2'].values, 
                        vowel_data['F1'].values, 
                        n_std=n_std
                    )
                    
                    if x_ellipse is not None:
                        fig.add_trace(go.Scatter(
                            x=x_ellipse,
                            y=y_ellipse,
                            mode='lines',
                            legendgroup=vowel,
                            line=dict(color=color, width=2),
                            fill='toself',
                            fillcolor=color,
                            opacity=0.2,
                            hoverinfo='skip',
                            showlegend=False
                        ))
                        
                        # Mean point with label
                        mean_f1 = vowel_data['F1'].mean()
                        mean_f2 = vowel_data['F2'].mean()
                        
                        fig.add_trace(go.Scatter(
                            x=[mean_f2],
                            y=[mean_f1],
                            mode='markers+text',
                            legendgroup=vowel,
                            marker=dict(size=14, color=color, symbol='circle',
                                      line=dict(width=2, color='white')),
                            text=vowel,
                            textposition='middle center',
                            textfont=dict(color='white', size=12, family='Arial Black'),
                            hovertext=f"<b>{vowel}</b><br>" +
                                     f"Mean F1: {mean_f1:.0f} Hz<br>Mean F2: {mean_f2:.0f} Hz<br>" +
                                     f"N = {len(vowel_data)}",
                            hoverinfo='text',
                            showlegend=False
                        ))
        
        # Invert axes
        fig.update_xaxes(
            autorange='reversed',
            title='F2 (Hz)',
            showgrid=True,
            gridcolor='lightgray'
        )
        fig.update_yaxes(
            autorange='reversed',
            title='F1 (Hz)',
            showgrid=True,
            gridcolor='lightgray'
        )
        
        # Update layout
        confidence_pct = int(confidence * 100)
        fig.update_layout(
            title=f'Vowel Space with {confidence_pct}% Confidence Ellipses<br>' +
                  f'<sub>Click legend to toggle • Double-click to isolate</sub>',
            width=1000,
            height=700,
            plot_bgcolor='white',
            hovermode='closest',
            font=dict(size=12),
            legend=dict(
                title=dict(
                    text='<b>Vowel Groups</b><br><sub>(click to toggle)</sub>',
                    font=dict(size=14)
                ),
                orientation='v',
                yanchor='top',
                y=1,
                xanchor='left',
                x=1.02,
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor='gray',
                borderwidth=1,
                itemclick='toggle',
                itemdoubleclick='toggleothers',
                tracegroupgap=10
            )
        )
        
        return json.loads(fig.to_json())
    
    except Exception as e:
        print(f"Error creating vowel space with ellipses: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def calculate_confidence_ellipse(x, y, n_std=2.0, n_points=100):
    """
    Calculate confidence ellipse for 2D data points
    
    Args:
        x: array of x coordinates (F2 values)
        y: array of y coordinates (F1 values)
        n_std: number of standard deviations (default 2.0 for ~95% confidence)
        n_points: number of points to use for ellipse perimeter
    
    Returns:
        tuple: (ellipse_x, ellipse_y) arrays for plotting
    """
    from scipy import stats
    
    if len(x) < 3 or len(y) < 3:
        return None, None
    
    # Calculate covariance matrix
    cov = np.cov(x, y)
    
    # Calculate eigenvalues and eigenvectors
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    
    # Sort by eigenvalue
    order = eigenvalues.argsort()[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    
    # Calculate ellipse angle
    angle = np.degrees(np.arctan2(*eigenvectors[:, 0][::-1]))
    
    # Width and height are the eigenvalues scaled by n_std
    width, height = 2 * n_std * np.sqrt(eigenvalues)
    
    # Generate ellipse points
    theta = np.linspace(0, 2 * np.pi, n_points)
    ellipse = np.array([width * np.cos(theta), height * np.sin(theta)])
    
    # Rotate ellipse
    rotation_matrix = np.array([
        [np.cos(np.radians(angle)), -np.sin(np.radians(angle))],
        [np.sin(np.radians(angle)), np.cos(np.radians(angle))]
    ])
    ellipse = rotation_matrix @ ellipse
    
    # Translate to center
    center_x = np.mean(x)
    center_y = np.mean(y)
    ellipse_x = ellipse[0] + center_x
    ellipse_y = ellipse[1] + center_y
    
    return ellipse_x, ellipse_y


def create_vowel_space_with_ellipses(df, confidence_level=0.95, show_points=True, scale='Hz'):
    """
    Create vowel space visualization with confidence ellipses
    
    Args:
        df: DataFrame with F1, F2, and optionally vowel, speaker, native_language
        confidence_level: confidence level for ellipses (0.95 = 95%)
        show_points: whether to show individual data points
        scale: Frequency scale label ('Hz', 'Bark', 'ERB', 'Mel')
    
    Returns:
        Plotly figure in JSON format
    """
    if df is None or df.empty:
        print("Error: Empty dataframe")
        return None
    
    try:
        # Convert confidence level to standard deviations
        # 95% ≈ 2 std, 99% ≈ 3 std
        if confidence_level >= 0.99:
            n_std = 1.0
        elif confidence_level >= 0.95:
            n_std = 1.0
        else:
            n_std = 1.0
        
        fig = go.Figure()
        
        # Determine grouping
        has_vowel = 'vowel' in df.columns
        has_speaker = 'speaker' in df.columns
        has_language = 'native_language' in df.columns
        
        colors = CUSTOM_COLORS
        color_idx = 0
        
        if has_vowel and has_speaker and has_language:
            # 3-level grouping
            for lang in sorted(df['native_language'].unique()):
                lang_data = df[df['native_language'] == lang]
                
                for speaker in sorted(lang_data['speaker'].unique()):
                    speaker_data = lang_data[lang_data['speaker'] == speaker]
                    
                    for vowel in sorted(speaker_data['vowel'].unique()):
                        vowel_data = speaker_data[speaker_data['vowel'] == vowel]
                        
                        if len(vowel_data) >= 3:
                            color = colors[color_idx % len(colors)]
                            
                            # Draw ellipse
                            ellipse_x, ellipse_y = calculate_confidence_ellipse(
                                vowel_data['F2'].values,
                                vowel_data['F1'].values,
                                n_std=n_std
                            )
                            
                            if ellipse_x is not None:
                                # Create hierarchical legend group: lang > speaker > individual vowel
                                fig.add_trace(go.Scatter(
                                    x=ellipse_x,
                                    y=ellipse_y,
                                    mode='lines',
                                    name=vowel,
                                    legendgroup=f"{lang}_{speaker}",
                                    legendgrouptitle=dict(text=f"{lang} - {speaker}"),
                                    line=dict(color=color, width=2),
                                    fill='none',
                                    hoverinfo='name'
                                ))
                            
                            # Optionally show points
                            if show_points:
                                fig.add_trace(go.Scatter(
                                    x=vowel_data['F2'],
                                    y=vowel_data['F1'],
                                    mode='markers',
                                    name=f"{vowel} (points)",
                                    legendgroup=f"{lang}_{speaker}",
                                    showlegend=False,
                                    marker=dict(size=5, color=color, opacity=0.5),
                                    hovertemplate=f"<b>{vowel}</b><br>Speaker: {speaker}<br>Language: {lang}<br>F1: %{{y:.0f}} Hz<br>F2: %{{x:.0f}} Hz<extra></extra>"
                                ))
                            
                            color_idx += 1
                            
        elif has_vowel and has_speaker:
            # 2-level grouping
            for speaker in sorted(df['speaker'].unique()):
                speaker_data = df[df['speaker'] == speaker]
                
                for vowel in sorted(speaker_data['vowel'].unique()):
                    vowel_data = speaker_data[speaker_data['vowel'] == vowel]
                    
                    if len(vowel_data) >= 3:
                        color = colors[color_idx % len(colors)]
                        
                        ellipse_x, ellipse_y = calculate_confidence_ellipse(
                            vowel_data['F2'].values,
                            vowel_data['F1'].values,
                            n_std=n_std
                        )
                        
                        if ellipse_x is not None:
                            fig.add_trace(go.Scatter(
                                x=ellipse_x,
                                y=ellipse_y,
                                mode='lines',
                                name=vowel,
                                legendgroup=speaker,
                                legendgrouptitle=dict(text=speaker),
                                line=dict(color=color, width=2),
                                fill='none',
                                hoverinfo='name'
                            ))
                        
                        if show_points:
                            fig.add_trace(go.Scatter(
                                x=vowel_data['F2'],
                                y=vowel_data['F1'],
                                mode='markers',
                                name=f"{vowel} (points)",
                                legendgroup=speaker,
                                showlegend=False,
                                marker=dict(size=5, color=color, opacity=0.5),
                                hovertemplate=f"<b>{vowel}</b><br>Speaker: {speaker}<br>F1: %{{y:.0f}} Hz<br>F2: %{{x:.0f}} Hz<extra></extra>"
                            ))
                        
                        color_idx += 1
                        
        elif has_vowel:
            # Single-level grouping by vowel
            for idx, vowel in enumerate(sorted(df['vowel'].unique())):
                vowel_data = df[df['vowel'] == vowel]
                
                if len(vowel_data) >= 3:
                    color = colors[idx % len(colors)]
                    
                    ellipse_x, ellipse_y = calculate_confidence_ellipse(
                        vowel_data['F2'].values,
                        vowel_data['F1'].values,
                        n_std=n_std
                    )
                    
                    if ellipse_x is not None:
                        fig.add_trace(go.Scatter(
                            x=ellipse_x,
                            y=ellipse_y,
                            mode='lines',
                            name=vowel,
                            line=dict(color=color, width=2),
                            fill='none',
                            hoverinfo='name'
                        ))
                    
                    if show_points:
                        fig.add_trace(go.Scatter(
                            x=vowel_data['F2'],
                            y=vowel_data['F1'],
                            mode='markers',
                            name=f"{vowel} (points)",
                            showlegend=False,
                            marker=dict(size=5, color=color, opacity=0.5),
                            hovertemplate=f"<b>{vowel}</b><br>F1: %{{y:.0f}} Hz<br>F2: %{{x:.0f}} Hz<extra></extra>"
                        ))
        
        # Invert axes and set fixed ranges
        fig.update_xaxes(
            range=[2700, 600],  # F2: 2700 to 600 (reversed)
            title=f'F2 ({scale})',
            showgrid=True,
            gridcolor='lightgray'
        )
        fig.update_yaxes(
            range=[1200, 100],  # F1: 1200 to 100 (reversed)
            title=f'F1 ({scale})',
            showgrid=True,
            gridcolor='lightgray'
        )
        
        # Update layout
        confidence_pct = int(confidence_level * 100)
        fig.update_layout(
            title=f'Vowel Space with {confidence_pct}% Confidence Ellipses - {scale}<br><sub>Click legend to show/hide • Double-click to isolate</sub>',
            width=1000,
            height=700,
            plot_bgcolor='white',
            hovermode='closest',
            font=dict(size=12),
            legend=dict(
                title=dict(
                    text='<b>Groups</b><br><sub>(click to toggle)</sub>',
                    font=dict(size=14)
                ),
                orientation='v',
                yanchor='top',
                y=1,
                xanchor='left',
                x=1.02,
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor='gray',
                borderwidth=1,
                itemclick='toggle',
                itemdoubleclick='toggleothers',
                tracegroupgap=5
            )
        )
        
        return json.loads(fig.to_json())
    
    except Exception as e:
        print(f"Error creating vowel space with ellipses: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def create_pca_plot(df_pca, pca_results, scale='Hz'):
    """
    Create PCA biplot visualization
    
    Args:
        df_pca: DataFrame with PC1, PC2 columns and original grouping
        pca_results: Dict with PCA results including explained variance
        scale: Frequency scale label ('Hz', 'Bark', 'ERB', 'Mel')
    
    Returns:
        JSON plot object
    """
    try:
        fig = go.Figure()
        
        # Determine grouping
        has_vowel = 'vowel' in df_pca.columns
        has_speaker = 'speaker' in df_pca.columns
        has_language = 'native_language' in df_pca.columns
        
        colors = CUSTOM_COLORS
        
        if has_vowel and has_speaker and has_language:
            # 3-level grouping
            color_idx = 0
            for lang in sorted(df_pca['native_language'].unique()):
                lang_data = df_pca[df_pca['native_language'] == lang]
                for speaker in sorted(lang_data['speaker'].unique()):
                    speaker_data = lang_data[lang_data['speaker'] == speaker]
                    for vowel in sorted(speaker_data['vowel'].unique()):
                        vowel_data = speaker_data[speaker_data['vowel'] == vowel]
                        
                        hover_text = [
                            f"<b>{vowel}</b><br>Speaker: {speaker}<br>Language: {lang}<br>" +
                            f"PC1: {pc1:.3f}<br>PC2: {pc2:.3f}"
                            for pc1, pc2 in zip(vowel_data['PC1'], vowel_data['PC2'])
                        ]
                        
                        fig.add_trace(go.Scatter(
                            x=vowel_data['PC1'],
                            y=vowel_data['PC2'],
                            mode='markers',
                            name=f"{lang} | {speaker} | {vowel}",
                            legendgroup=lang,
                            legendgrouptitle=dict(text=lang),
                            marker=dict(size=10, color=colors[color_idx % len(colors)], opacity=0.7),
                            text=hover_text,
                            hoverinfo='text'
                        ))
                        color_idx += 1
        elif has_vowel:
            for idx, vowel in enumerate(sorted(df_pca['vowel'].unique())):
                vowel_data = df_pca[df_pca['vowel'] == vowel]
                
                hover_text = [
                    f"<b>{vowel}</b><br>PC1: {pc1:.3f}<br>PC2: {pc2:.3f}"
                    for pc1, pc2 in zip(vowel_data['PC1'], vowel_data['PC2'])
                ]
                
                fig.add_trace(go.Scatter(
                    x=vowel_data['PC1'],
                    y=vowel_data['PC2'],
                    mode='markers',
                    name=vowel,
                    marker=dict(size=10, color=colors[idx % len(colors)], opacity=0.7),
                    text=hover_text,
                    hoverinfo='text'
                ))
        else:
            hover_text = [
                f"PC1: {pc1:.3f}<br>PC2: {pc2:.3f}"
                for pc1, pc2 in zip(df_pca['PC1'], df_pca['PC2'])
            ]
            
            fig.add_trace(go.Scatter(
                x=df_pca['PC1'],
                y=df_pca['PC2'],
                mode='markers',
                marker=dict(size=10, color='blue', opacity=0.7),
                text=hover_text,
                hoverinfo='text'
            ))
        
        # Get explained variance
        var_pc1 = pca_results.get('explained_variance_ratio', [0, 0])[0] * 100
        var_pc2 = pca_results.get('explained_variance_ratio', [0, 0])[1] * 100
        
        fig.update_layout(
            title=f'PCA Biplot ({scale})<br><sub>Total variance explained: {var_pc1 + var_pc2:.1f}%</sub>',
            xaxis_title=f'PC1 ({var_pc1:.1f}% variance)',
            yaxis_title=f'PC2 ({var_pc2:.1f}% variance)',
            width=1000,
            height=700,
            plot_bgcolor='white',
            hovermode='closest',
            font=dict(size=12),
            legend=dict(
                title='Groups',
                orientation='v',
                yanchor='top',
                y=1,
                xanchor='left',
                x=1.02
            )
        )
        
        # Add grid
        fig.update_xaxes(showgrid=True, gridcolor='lightgray', zeroline=True, zerolinecolor='black')
        fig.update_yaxes(showgrid=True, gridcolor='lightgray', zeroline=True, zerolinecolor='black')
        
        return json.loads(fig.to_json())
    
    except Exception as e:
        print(f"Error creating PCA plot: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def create_lda_plot(df_lda, lda_results, group_by='vowel', scale='Hz'):
    """
    Create LDA plot visualization
    
    Args:
        df_lda: DataFrame with LD1, LD2 columns and grouping
        lda_results: Dict with LDA results
        group_by: Grouping variable name
        scale: Frequency scale label ('Hz', 'Bark', 'ERB', 'Mel')
    
    Returns:
        JSON plot object
    """
    try:
        fig = go.Figure()
        
        colors = CUSTOM_COLORS
        
        if group_by in df_lda.columns:
            for idx, group in enumerate(sorted(df_lda[group_by].unique())):
                group_data = df_lda[df_lda[group_by] == group]
                
                hover_text = [
                    f"<b>{group}</b><br>LD1: {ld1:.3f}<br>LD2: {ld2:.3f}"
                    for ld1, ld2 in zip(group_data['LD1'], group_data['LD2'])
                ]
                
                fig.add_trace(go.Scatter(
                    x=group_data['LD1'],
                    y=group_data['LD2'],
                    mode='markers',
                    name=str(group),
                    marker=dict(size=10, color=colors[idx % len(colors)], opacity=0.7),
                    text=hover_text,
                    hoverinfo='text'
                ))
        
        # Get accuracy
        accuracy = lda_results.get('accuracy', 0) * 100
        n_components = lda_results.get('n_components', 2)
        
        title = f'Linear Discriminant Analysis ({scale})<br><sub>Classification accuracy: {accuracy:.1f}%</sub>'
        
        fig.update_layout(
            title=title,
            xaxis_title='LD1 (Linear Discriminant 1)',
            yaxis_title='LD2 (Linear Discriminant 2)' if n_components > 1 else 'LD2',
            width=1000,
            height=700,
            plot_bgcolor='white',
            hovermode='closest',
            font=dict(size=12),
            legend=dict(
                title=f'Actual {group_by}',
                orientation='v',
                yanchor='top',
                y=1,
                xanchor='left',
                x=1.02
            )
        )
        
        # Add grid
        fig.update_xaxes(showgrid=True, gridcolor='lightgray', zeroline=True, zerolinecolor='black')
        fig.update_yaxes(showgrid=True, gridcolor='lightgray', zeroline=True, zerolinecolor='black')
        
        return json.loads(fig.to_json())
    
    except Exception as e:
        print(f"Error creating LDA plot: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def create_boxplot(df, group_by='vowel', scale='Hz'):
    """
    Create box plots for F1 and F2 by group
    
    Args:
        df: DataFrame with F1, F2 columns
        group_by: Column to group by (default: 'vowel')
        scale: Frequency scale label
    
    Returns:
        JSON representation of the plot
    """
    if df is None or df.empty or group_by not in df.columns:
        return None
    
    try:
        from plotly.subplots import make_subplots
        
        # Create subplots for F1 and F2
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=(f'F1 by {group_by}', f'F2 by {group_by}'),
            horizontal_spacing=0.15
        )
        
        colors = CUSTOM_COLORS
        groups = sorted(df[group_by].unique())
        
        for i, group in enumerate(groups):
            group_data = df[df[group_by] == group]
            color = colors[i % len(colors)]
            
            # F1 boxplot
            fig.add_trace(
                go.Box(
                    y=group_data['F1'],
                    name=str(group),
                    marker_color=color,
                    showlegend=False,
                    boxmean='sd'  # Show mean and standard deviation
                ),
                row=1, col=1
            )
            
            # F2 boxplot
            fig.add_trace(
                go.Box(
                    y=group_data['F2'],
                    name=str(group),
                    marker_color=color,
                    showlegend=True,
                    legendgroup=str(group),
                    boxmean='sd'
                ),
                row=1, col=2
            )
        
        fig.update_layout(
            title=f'Formant Distribution by {group_by}',
            height=500,
            width=1000,
            plot_bgcolor='white',
            font=dict(size=12),
            showlegend=True,
            legend=dict(
                title=group_by,
                orientation='v',
                yanchor='top',
                y=1,
                xanchor='left',
                x=1.02
            )
        )
        
        fig.update_yaxes(title_text=f"F1 ({scale})", row=1, col=1, showgrid=True, gridcolor='lightgray')
        fig.update_yaxes(title_text=f"F2 ({scale})", row=1, col=2, showgrid=True, gridcolor='lightgray')
        fig.update_xaxes(title_text=group_by, row=1, col=1)
        fig.update_xaxes(title_text=group_by, row=1, col=2)
        
        return json.loads(fig.to_json())
    
    except Exception as e:
        print(f"Error creating boxplot: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def create_violin_plot(df, group_by='vowel', scale='Hz'):
    """
    Create violin plots for F1 and F2 by group
    
    Args:
        df: DataFrame with F1, F2 columns
        group_by: Column to group by (default: 'vowel')
        scale: Frequency scale label
    
    Returns:
        JSON representation of the plot
    """
    if df is None or df.empty or group_by not in df.columns:
        return None
    
    try:
        from plotly.subplots import make_subplots
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=(f'F1 Distribution by {group_by}', f'F2 Distribution by {group_by}'),
            horizontal_spacing=0.15
        )
        
        colors = CUSTOM_COLORS
        groups = sorted(df[group_by].unique())
        
        for i, group in enumerate(groups):
            group_data = df[df[group_by] == group]
            color = colors[i % len(colors)]
            
            # F1 violin
            fig.add_trace(
                go.Violin(
                    y=group_data['F1'],
                    name=str(group),
                    fillcolor=color,
                    line_color='black',
                    showlegend=False,
                    box_visible=True,
                    meanline_visible=True
                ),
                row=1, col=1
            )
            
            # F2 violin
            fig.add_trace(
                go.Violin(
                    y=group_data['F2'],
                    name=str(group),
                    fillcolor=color,
                    line_color='black',
                    showlegend=True,
                    legendgroup=str(group),
                    box_visible=True,
                    meanline_visible=True
                ),
                row=1, col=2
            )
        
        fig.update_layout(
            title=f'Formant Distribution (Violin Plot) by {group_by}',
            height=500,
            width=1000,
            plot_bgcolor='white',
            font=dict(size=12),
            showlegend=True,
            legend=dict(
                title=group_by,
                orientation='v',
                yanchor='top',
                y=1,
                xanchor='left',
                x=1.02
            )
        )
        
        fig.update_yaxes(title_text=f"F1 ({scale})", row=1, col=1, showgrid=True, gridcolor='lightgray')
        fig.update_yaxes(title_text=f"F2 ({scale})", row=1, col=2, showgrid=True, gridcolor='lightgray')
        fig.update_xaxes(title_text=group_by, row=1, col=1)
        fig.update_xaxes(title_text=group_by, row=1, col=2)
        
        return json.loads(fig.to_json())
    
    except Exception as e:
        print(f"Error creating violin plot: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def create_histogram(df, group_by='vowel', scale='Hz'):
    """
    Create density plots for F1 and F2 distributions
    
    Args:
        df: DataFrame with F1, F2 columns
        group_by: Column to group by (default: 'vowel')
        scale: Frequency scale label
    
    Returns:
        JSON representation of the plot
    """
    if df is None or df.empty:
        return None
    
    try:
        from plotly.subplots import make_subplots
        from scipy.stats import gaussian_kde
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('F1 Distribution (Density)', 'F2 Distribution (Density)'),
            horizontal_spacing=0.15
        )
        
        if group_by and group_by in df.columns:
            colors = CUSTOM_COLORS
            groups = sorted(df[group_by].unique())
            
            for i, group in enumerate(groups):
                group_data = df[df[group_by] == group]
                color = colors[i % len(colors)]
                
                # F1 density plot
                if len(group_data['F1'].dropna()) > 1:
                    f1_values = group_data['F1'].dropna().values
                    kde_f1 = gaussian_kde(f1_values)
                    x_f1 = np.linspace(f1_values.min(), f1_values.max(), 200)
                    y_f1 = kde_f1(x_f1)
                    
                    fig.add_trace(
                        go.Scatter(
                            x=x_f1,
                            y=y_f1,
                            name=str(group),
                            mode='lines',
                            line=dict(color=color, width=2.5),
                            showlegend=False,
                            hovertemplate='<b>%{fullData.name}</b><br>' +
                                        'F1: %{x:.1f}<br>' +
                                        'Density: %{y:.4f}<br>' +
                                        '<extra></extra>'
                        ),
                        row=1, col=1
                    )
                
                # F2 density plot
                if len(group_data['F2'].dropna()) > 1:
                    f2_values = group_data['F2'].dropna().values
                    kde_f2 = gaussian_kde(f2_values)
                    x_f2 = np.linspace(f2_values.min(), f2_values.max(), 200)
                    y_f2 = kde_f2(x_f2)
                    
                    fig.add_trace(
                        go.Scatter(
                            x=x_f2,
                            y=y_f2,
                            name=str(group),
                            mode='lines',
                            line=dict(color=color, width=2.5),
                            showlegend=True,
                            legendgroup=str(group),
                            hovertemplate='<b>%{fullData.name}</b><br>' +
                                        'F2: %{x:.1f}<br>' +
                                        'Density: %{y:.4f}<br>' +
                                        '<extra></extra>'
                        ),
                        row=1, col=2
                    )
        else:
            # Overall density plots without grouping
            if len(df['F1'].dropna()) > 1:
                f1_values = df['F1'].dropna().values
                kde_f1 = gaussian_kde(f1_values)
                x_f1 = np.linspace(f1_values.min(), f1_values.max(), 200)
                y_f1 = kde_f1(x_f1)
                
                fig.add_trace(
                    go.Scatter(
                        x=x_f1,
                        y=y_f1,
                        mode='lines',
                        line=dict(color='steelblue', width=3),
                        showlegend=False,
                        hovertemplate='F1: %{x:.1f}<br>' +
                                    'Density: %{y:.4f}<br>' +
                                    '<extra></extra>'
                    ),
                    row=1, col=1
                )
            
            if len(df['F2'].dropna()) > 1:
                f2_values = df['F2'].dropna().values
                kde_f2 = gaussian_kde(f2_values)
                x_f2 = np.linspace(f2_values.min(), f2_values.max(), 200)
                y_f2 = kde_f2(x_f2)
                
                fig.add_trace(
                    go.Scatter(
                        x=x_f2,
                        y=y_f2,
                        mode='lines',
                        line=dict(color='coral', width=3),
                        showlegend=False,
                        hovertemplate='F2: %{x:.1f}<br>' +
                                    'Density: %{y:.4f}<br>' +
                                    '<extra></extra>'
                    ),
                    row=1, col=2
                )
        
        title = f'Formant Distribution (Density Plot)'
        if group_by and group_by in df.columns:
            title += f' by {group_by}'
        
        fig.update_layout(
            title=title,
            height=500,
            width=1000,
            plot_bgcolor='white',
            font=dict(size=12),
            showlegend=True if group_by and group_by in df.columns else False,
            legend=dict(
                title=group_by if group_by and group_by in df.columns else None,
                orientation='v',
                yanchor='top',
                y=1,
                xanchor='left',
                x=1.02
            )
        )
        
        fig.update_xaxes(title_text=f"F1 ({scale})", row=1, col=1, showgrid=True, gridcolor='lightgray')
        fig.update_xaxes(title_text=f"F2 ({scale})", row=1, col=2, showgrid=True, gridcolor='lightgray')
        fig.update_yaxes(title_text="Density", row=1, col=1, showgrid=True, gridcolor='lightgray')
        fig.update_yaxes(title_text="Density", row=1, col=2, showgrid=True, gridcolor='lightgray')
        
        return json.loads(fig.to_json())
    
    except Exception as e:
        print(f"Error creating histogram: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def create_scatter_matrix(df, color_by='vowel'):
    """
    Create a scatter matrix showing relationships between F1, F2, and other variables
    
    Args:
        df: DataFrame with F1, F2 columns
        color_by: Column to color by (default: 'vowel')
    
    Returns:
        JSON representation of the plot
    """
    if df is None or df.empty:
        return None
    
    try:
        # Select relevant columns
        dimensions = ['F1', 'F2']
        if 'F3' in df.columns:
            dimensions.append('F3')
        
        color_column = color_by if color_by in df.columns else None
        
        if color_column:
            fig = px.scatter_matrix(
                df,
                dimensions=dimensions,
                color=color_column,
                title=f'Scatter Matrix (colored by {color_by})',
                height=800,
                width=800,
                opacity=0.7
            )
        else:
            fig = px.scatter_matrix(
                df,
                dimensions=dimensions,
                title='Scatter Matrix',
                height=800,
                width=800,
                opacity=0.7
            )
        
        fig.update_traces(diagonal_visible=True, showupperhalf=False)
        fig.update_layout(
            plot_bgcolor='white',
            font=dict(size=10)
        )
        
        return json.loads(fig.to_json())
    
    except Exception as e:
        print(f"Error creating scatter matrix: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def create_mean_comparison_plot(df, group_by='vowel', scale='Hz'):
    """
    Create a plot comparing means with error bars across groups
    
    Args:
        df: DataFrame with F1, F2 columns
        group_by: Column to group by (default: 'vowel')
        scale: Frequency scale label
    
    Returns:
        JSON representation of the plot
    """
    if df is None or df.empty or group_by not in df.columns:
        return None
    
    try:
        from plotly.subplots import make_subplots
        
        # Calculate statistics by group
        stats_data = []
        for group in sorted(df[group_by].unique()):
            group_data = df[df[group_by] == group]
            stats_data.append({
                'group': str(group),
                'f1_mean': group_data['F1'].mean(),
                'f1_std': group_data['F1'].std(),
                'f1_se': group_data['F1'].sem(),
                'f2_mean': group_data['F2'].mean(),
                'f2_std': group_data['F2'].std(),
                'f2_se': group_data['F2'].sem(),
                'count': len(group_data)
            })
        
        stats_df = pd.DataFrame(stats_data)
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=(f'F1 Mean ± SE by {group_by}', f'F2 Mean ± SE by {group_by}'),
            horizontal_spacing=0.15
        )
        
        colors = CUSTOM_COLORS
        
        # F1 bar chart with error bars
        fig.add_trace(
            go.Bar(
                x=stats_df['group'],
                y=stats_df['f1_mean'],
                error_y=dict(type='data', array=stats_df['f1_se']),
                marker_color=colors[0],
                showlegend=False,
                text=[f"n={n}" for n in stats_df['count']],
                textposition='outside'
            ),
            row=1, col=1
        )
        
        # F2 bar chart with error bars
        fig.add_trace(
            go.Bar(
                x=stats_df['group'],
                y=stats_df['f2_mean'],
                error_y=dict(type='data', array=stats_df['f2_se']),
                marker_color=colors[1],
                showlegend=False,
                text=[f"n={n}" for n in stats_df['count']],
                textposition='outside'
            ),
            row=1, col=2
        )
        
        fig.update_layout(
            title=f'Mean Formant Values with Standard Error by {group_by}',
            height=500,
            width=1000,
            plot_bgcolor='white',
            font=dict(size=12)
        )
        
        fig.update_yaxes(title_text=f"F1 Mean ({scale})", row=1, col=1, showgrid=True, gridcolor='lightgray')
        fig.update_yaxes(title_text=f"F2 Mean ({scale})", row=1, col=2, showgrid=True, gridcolor='lightgray')
        fig.update_xaxes(title_text=group_by, row=1, col=1)
        fig.update_xaxes(title_text=group_by, row=1, col=2)
        
        return json.loads(fig.to_json())
    
    except Exception as e:
        print(f"Error creating mean comparison plot: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def create_pairwise_comparison_plot(pairwise_results, scale='Hz'):
    """
    Create bar graph for pairwise test results with significance markers
    
    Args:
        pairwise_results: dict with pairwise test results from perform_pairwise_tests()
        scale: 'Hz' or 'Bark'
    
    Returns:
        JSON plot object
    """
    if pairwise_results is None or 'error' in pairwise_results:
        return None
    
    try:
        from plotly.subplots import make_subplots
        
        comparisons = pairwise_results.get('comparisons', {})
        if not comparisons:
            return None
        
        # Extract comparison data
        comparison_labels = []
        f1_mean_diffs = []
        f1_p_values = []
        f2_mean_diffs = []
        f2_p_values = []
        
        for comp_key, comp_data in sorted(comparisons.items()):
            # Format label (e.g., "a vs e")
            label = comp_key.replace('_vs_', ' vs ')
            comparison_labels.append(label)
            
            # F1 data
            if 'F1' in comp_data:
                f1_mean_diffs.append(abs(comp_data['F1']['mean_diff']))
                f1_p_values.append(comp_data['F1']['p_value'])
            else:
                f1_mean_diffs.append(0)
                f1_p_values.append(1)
            
            # F2 data
            if 'F2' in comp_data:
                f2_mean_diffs.append(abs(comp_data['F2']['mean_diff']))
                f2_p_values.append(comp_data['F2']['p_value'])
            else:
                f2_mean_diffs.append(0)
                f2_p_values.append(1)
        
        # Create significance markers
        def get_significance_marker(p_value):
            if p_value < 0.001:
                return '***'
            elif p_value < 0.01:
                return '**'
            elif p_value < 0.05:
                return '*'
            else:
                return 'ns'
        
        f1_sig = [get_significance_marker(p) for p in f1_p_values]
        f2_sig = [get_significance_marker(p) for p in f2_p_values]
        
        # Create subplots
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=(f'F1 Mean Difference ({scale})', f'F2 Mean Difference ({scale})'),
            horizontal_spacing=0.15
        )
        
        # F1 bar chart
        bar_colors_f1 = [CUSTOM_COLORS[0] if sig != 'ns' else '#cccccc' for sig in f1_sig]
        fig.add_trace(
            go.Bar(
                x=comparison_labels,
                y=f1_mean_diffs,
                name='F1',
                marker_color=bar_colors_f1,
                text=f1_sig,
                textposition='outside',
                textfont=dict(size=14, color='black'),
                hovertemplate='%{x}<br>Mean Diff: %{y:.1f} Hz<br>Significance: %{text}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # F2 bar chart
        bar_colors_f2 = [CUSTOM_COLORS[1] if sig != 'ns' else '#cccccc' for sig in f2_sig]
        fig.add_trace(
            go.Bar(
                x=comparison_labels,
                y=f2_mean_diffs,
                name='F2',
                marker_color=bar_colors_f2,
                text=f2_sig,
                textposition='outside',
                textfont=dict(size=14, color='black'),
                hovertemplate='%{x}<br>Mean Diff: %{y:.1f} Hz<br>Significance: %{text}<extra></extra>'
            ),
            row=1, col=2
        )
        
        # Update layout
        fig.update_layout(
            title=f"Pairwise Comparisons: Mean Differences (by {pairwise_results.get('group_by', 'group')})",
            height=500,
            width=900,
            showlegend=False,
            plot_bgcolor='white',
            font=dict(size=12)
        )
        
        fig.update_yaxes(title_text=f"Absolute Mean Difference ({scale})", row=1, col=1, showgrid=True, gridcolor='lightgray')
        fig.update_yaxes(title_text=f"Absolute Mean Difference ({scale})", row=1, col=2, showgrid=True, gridcolor='lightgray')
        fig.update_xaxes(row=1, col=1, tickangle=-45)
        fig.update_xaxes(row=1, col=2, tickangle=-45)
        
        return json.loads(fig.to_json())
    
    except Exception as e:
        print(f"Error creating pairwise comparison plot: {e}")
        import traceback
        print(traceback.format_exc())
        return None

