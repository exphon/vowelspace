"""
Formant frequency scale conversions
Supports: Hz, Bark, ERB, Mel scales
"""
import numpy as np


def hz_to_bark(hz):
    """
    Convert Hz to Bark scale using Traunmüller (1990) formula
    
    Args:
        hz: Frequency in Hz (scalar or array)
    
    Returns:
        Frequency in Bark
    """
    hz = np.asarray(hz)
    return 26.81 * hz / (1960 + hz) - 0.53


def bark_to_hz(bark):
    """
    Convert Bark to Hz using Traunmüller (1990) formula
    
    Args:
        bark: Frequency in Bark (scalar or array)
    
    Returns:
        Frequency in Hz
    """
    bark = np.asarray(bark)
    return 1960 * (bark + 0.53) / (26.81 - bark)


def hz_to_erb(hz):
    """
    Convert Hz to ERB (Equivalent Rectangular Bandwidth) scale
    Using Glasberg & Moore (1990) formula
    
    Args:
        hz: Frequency in Hz (scalar or array)
    
    Returns:
        Frequency in ERB
    """
    hz = np.asarray(hz)
    return 21.4 * np.log10(1 + 0.00437 * hz)


def erb_to_hz(erb):
    """
    Convert ERB to Hz using Glasberg & Moore (1990) formula
    
    Args:
        erb: Frequency in ERB (scalar or array)
    
    Returns:
        Frequency in Hz
    """
    erb = np.asarray(erb)
    return (10 ** (erb / 21.4) - 1) / 0.00437


def hz_to_mel(hz):
    """
    Convert Hz to Mel scale using O'Shaughnessy (1987) formula
    
    Args:
        hz: Frequency in Hz (scalar or array)
    
    Returns:
        Frequency in Mel
    """
    hz = np.asarray(hz)
    return 2595 * np.log10(1 + hz / 700)


def mel_to_hz(mel):
    """
    Convert Mel to Hz using O'Shaughnessy (1987) formula
    
    Args:
        mel: Frequency in Mel (scalar or array)
    
    Returns:
        Frequency in Hz
    """
    mel = np.asarray(mel)
    return 700 * (10 ** (mel / 2595) - 1)


def convert_formants(df, from_scale='Hz', to_scale='Bark', formant_cols=['F1', 'F2']):
    """
    Convert formant frequencies between different scales
    
    Args:
        df: DataFrame with formant columns
        from_scale: Source scale ('Hz', 'Bark', 'ERB', 'Mel')
        to_scale: Target scale ('Hz', 'Bark', 'ERB', 'Mel')
        formant_cols: List of formant column names to convert
    
    Returns:
        DataFrame with converted formant values
    """
    if from_scale == to_scale:
        return df.copy()
    
    df_converted = df.copy()
    
    # Define conversion functions
    conversions = {
        ('Hz', 'Bark'): hz_to_bark,
        ('Hz', 'ERB'): hz_to_erb,
        ('Hz', 'Mel'): hz_to_mel,
        ('Bark', 'Hz'): bark_to_hz,
        ('ERB', 'Hz'): erb_to_hz,
        ('Mel', 'Hz'): mel_to_hz,
    }
    
    # Two-step conversion for non-Hz to non-Hz
    if from_scale != 'Hz' and to_scale != 'Hz':
        # First convert to Hz
        if (from_scale, 'Hz') in conversions:
            for col in formant_cols:
                if col in df_converted.columns:
                    df_converted[col] = conversions[(from_scale, 'Hz')](df_converted[col])
        
        # Then convert from Hz to target
        if ('Hz', to_scale) in conversions:
            for col in formant_cols:
                if col in df_converted.columns:
                    df_converted[col] = conversions[('Hz', to_scale)](df_converted[col])
    else:
        # Direct conversion
        if (from_scale, to_scale) in conversions:
            for col in formant_cols:
                if col in df_converted.columns:
                    df_converted[col] = conversions[(from_scale, to_scale)](df_converted[col])
    
    return df_converted


def get_scale_label(scale):
    """
    Get axis label for a given scale
    
    Args:
        scale: Scale name ('Hz', 'Bark', 'ERB', 'Mel')
    
    Returns:
        Formatted label string
    """
    labels = {
        'Hz': 'Hz',
        'Bark': 'Bark',
        'ERB': 'ERB',
        'Mel': 'Mel'
    }
    return labels.get(scale, scale)


def get_available_scales():
    """
    Get list of available frequency scales
    
    Returns:
        List of scale names
    """
    return ['Hz', 'Bark', 'ERB', 'Mel']
