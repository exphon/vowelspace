"""
Statistical analysis utilities for vowel space data
Includes multivariate analysis: MANOVA, PCA, LDA, descriptive statistics
"""
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


def calculate_descriptive_statistics(df, group_by=None):
    """
    Calculate descriptive statistics for F1 and F2
    
    Args:
        df: DataFrame with F1, F2 columns
        group_by: Column name to group by (e.g., 'vowel', 'speaker', 'native_language')
    
    Returns:
        dict with statistics
    """
    results = {
        'overall': {},
        'by_group': {}
    }
    
    # Overall statistics
    for formant in ['F1', 'F2']:
        if formant in df.columns:
            results['overall'][formant] = {
                'mean': float(df[formant].mean()),
                'std': float(df[formant].std()),
                'min': float(df[formant].min()),
                'max': float(df[formant].max()),
                'median': float(df[formant].median()),
                'q25': float(df[formant].quantile(0.25)),
                'q75': float(df[formant].quantile(0.75)),
                'count': int(df[formant].count())
            }
    
    # Group-wise statistics
    if group_by and group_by in df.columns:
        for group in df[group_by].unique():
            group_data = df[df[group_by] == group]
            results['by_group'][str(group)] = {}
            
            for formant in ['F1', 'F2']:
                if formant in group_data.columns:
                    results['by_group'][str(group)][formant] = {
                        'mean': float(group_data[formant].mean()),
                        'std': float(group_data[formant].std()),
                        'min': float(group_data[formant].min()),
                        'max': float(group_data[formant].max()),
                        'median': float(group_data[formant].median()),
                        'count': int(group_data[formant].count())
                    }
    
    return results


def perform_manova(df, group_by='vowel'):
    """
    Perform MANOVA (Multivariate Analysis of Variance)
    Tests if groups differ significantly in F1 and F2
    
    Args:
        df: DataFrame with F1, F2, and grouping column
        group_by: Column name for grouping (default: 'vowel')
    
    Returns:
        dict with MANOVA results
    """
    if group_by not in df.columns:
        return {'error': f'Column {group_by} not found'}
    
    # Prepare data
    groups = df[group_by].unique()
    
    if len(groups) < 2:
        return {'error': 'Need at least 2 groups for MANOVA'}
    
    # One-way MANOVA using Pillai's trace approximation
    # For each formant, perform ANOVA
    results = {
        'group_by': group_by,
        'n_groups': len(groups),
        'groups': list(map(str, groups)),
        'formants': {}
    }
    
    for formant in ['F1', 'F2']:
        if formant in df.columns:
            # Prepare data for ANOVA
            group_data = [df[df[group_by] == g][formant].dropna().values for g in groups]
            
            # Perform one-way ANOVA
            f_stat, p_value = stats.f_oneway(*group_data)
            
            results['formants'][formant] = {
                'f_statistic': float(f_stat),
                'p_value': float(p_value),
                'significant': p_value < 0.05,
                'significance_level': '***' if p_value < 0.001 else '**' if p_value < 0.01 else '*' if p_value < 0.05 else 'ns'
            }
    
    # Overall multivariate test (Hotelling's T-squared approximation)
    # Using Wilks' Lambda approach
    try:
        from scipy.stats import f as f_dist
        
        # Calculate group means
        X = df[['F1', 'F2']].values
        y = df[group_by].values
        
        # Between-group and within-group scatter matrices
        overall_mean = X.mean(axis=0)
        n_total = len(X)
        n_groups_val = len(groups)
        
        # Calculate Wilks' Lambda
        W = np.zeros((2, 2))  # Within-group scatter
        B = np.zeros((2, 2))  # Between-group scatter
        
        for group in groups:
            group_mask = y == group
            X_group = X[group_mask]
            n_group = len(X_group)
            
            if n_group > 1:
                group_mean = X_group.mean(axis=0)
                
                # Within-group scatter
                for xi in X_group:
                    diff = xi - group_mean
                    W += np.outer(diff, diff)
                
                # Between-group scatter
                diff_mean = group_mean - overall_mean
                B += n_group * np.outer(diff_mean, diff_mean)
        
        # Wilks' Lambda
        det_W = np.linalg.det(W)
        det_total = np.linalg.det(W + B)
        
        if det_total > 0:
            wilks_lambda = det_W / det_total
            
            # Convert to F-statistic (approximation)
            p = 2  # number of dependent variables
            k = n_groups_val - 1  # degrees of freedom for groups
            n = n_total - n_groups_val  # degrees of freedom for error
            
            results['multivariate'] = {
                'test': 'Wilks Lambda',
                'statistic': float(wilks_lambda),
                'interpretation': 'Smaller values indicate greater group separation'
            }
    except Exception as e:
        results['multivariate'] = {'error': str(e)}
    
    return results


def perform_pca(df):
    """
    Perform Principal Component Analysis on F1 and F2
    
    Args:
        df: DataFrame with F1, F2 columns
    
    Returns:
        dict with PCA results and transformed data
    """
    # Prepare data
    X = df[['F1', 'F2']].values
    
    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Perform PCA
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)
    
    # Create results
    results = {
        'explained_variance': pca.explained_variance_.tolist(),
        'explained_variance_ratio': pca.explained_variance_ratio_.tolist(),
        'cumulative_variance_ratio': np.cumsum(pca.explained_variance_ratio_).tolist(),
        'components': pca.components_.tolist(),
        'mean': scaler.mean_.tolist(),
        'scale': scaler.scale_.tolist()
    }
    
    # Add transformed coordinates to dataframe
    df_result = df.copy()
    df_result['PC1'] = X_pca[:, 0]
    df_result['PC2'] = X_pca[:, 1]
    
    return results, df_result


def perform_lda(df, group_by='vowel'):
    """
    Perform Linear Discriminant Analysis
    
    Args:
        df: DataFrame with F1, F2, and grouping column
        group_by: Column name for grouping
    
    Returns:
        dict with LDA results and transformed data
    """
    if group_by not in df.columns:
        return {'error': f'Column {group_by} not found'}, df
    
    # Prepare data
    X = df[['F1', 'F2']].values
    y = df[group_by].values
    
    # Check number of groups
    n_groups = len(np.unique(y))
    
    if n_groups < 2:
        return {'error': 'Need at least 2 groups for LDA'}, df
    
    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Perform LDA
    n_components = min(n_groups - 1, 2)
    lda = LinearDiscriminantAnalysis(n_components=n_components)
    X_lda = lda.fit_transform(X_scaled, y)
    
    # Calculate accuracy
    y_pred = lda.predict(X_scaled)
    accuracy = float(np.mean(y_pred == y))
    
    # Create results
    results = {
        'n_components': n_components,
        'explained_variance_ratio': lda.explained_variance_ratio_.tolist() if hasattr(lda, 'explained_variance_ratio_') else None,
        'accuracy': accuracy,
        'n_groups': n_groups,
        'groups': list(map(str, np.unique(y))),
        'group_by': group_by
    }
    
    # Add transformed coordinates to dataframe
    df_result = df.copy()
    df_result['LD1'] = X_lda[:, 0]
    if n_components > 1:
        df_result['LD2'] = X_lda[:, 1]
    else:
        df_result['LD2'] = 0
    
    df_result['predicted_' + group_by] = y_pred
    
    return results, df_result


def perform_pairwise_tests(df, group_by='vowel'):
    """
    Perform pairwise t-tests between groups for F1 and F2
    
    Args:
        df: DataFrame with F1, F2, and grouping column
        group_by: Column name for grouping
    
    Returns:
        dict with pairwise comparison results
    """
    if group_by not in df.columns:
        return {'error': f'Column {group_by} not found'}
    
    groups = df[group_by].unique()
    
    if len(groups) < 2:
        return {'error': 'Need at least 2 groups for pairwise tests'}
    
    results = {
        'group_by': group_by,
        'comparisons': {}
    }
    
    # Pairwise comparisons
    for i, group1 in enumerate(groups):
        for group2 in groups[i+1:]:
            comparison_key = f"{group1}_vs_{group2}"
            results['comparisons'][comparison_key] = {}
            
            data1 = df[df[group_by] == group1]
            data2 = df[df[group_by] == group2]
            
            for formant in ['F1', 'F2']:
                if formant in df.columns:
                    vals1 = data1[formant].dropna().values
                    vals2 = data2[formant].dropna().values
                    
                    if len(vals1) > 0 and len(vals2) > 0:
                        # Perform t-test
                        t_stat, p_value = stats.ttest_ind(vals1, vals2)
                        
                        # Calculate Cohen's d (effect size)
                        pooled_std = np.sqrt(((len(vals1)-1)*np.var(vals1, ddof=1) + 
                                               (len(vals2)-1)*np.var(vals2, ddof=1)) / 
                                              (len(vals1) + len(vals2) - 2))
                        cohens_d = (np.mean(vals1) - np.mean(vals2)) / pooled_std if pooled_std > 0 else 0
                        
                        results['comparisons'][comparison_key][formant] = {
                            't_statistic': float(t_stat),
                            'p_value': float(p_value),
                            'cohens_d': float(cohens_d),
                            'significant': p_value < 0.05,
                            'mean_diff': float(np.mean(vals1) - np.mean(vals2))
                        }
    
    return results


def calculate_vowel_space_metrics(df, group_by=None):
    """
    Calculate vowel space area and dispersion metrics
    
    Args:
        df: DataFrame with F1, F2 columns
        group_by: Optional grouping column
    
    Returns:
        dict with vowel space metrics
    """
    from scipy.spatial import ConvexHull
    
    results = {}
    
    def calc_metrics(data):
        if len(data) < 3:
            return None
        
        points = data[['F1', 'F2']].values
        
        try:
            hull = ConvexHull(points)
            area = float(hull.volume)  # In 2D, volume is area
            
            # Calculate centroid
            centroid = points.mean(axis=0)
            
            # Calculate dispersion (average distance from centroid)
            distances = np.sqrt(np.sum((points - centroid)**2, axis=1))
            dispersion = float(np.mean(distances))
            
            return {
                'area': area,
                'perimeter': float(hull.area),  # In 2D, area is perimeter
                'n_vertices': len(hull.vertices),
                'centroid_F1': float(centroid[0]),
                'centroid_F2': float(centroid[1]),
                'dispersion': dispersion,
                'n_points': len(data)
            }
        except Exception as e:
            return {'error': str(e)}
    
    # Overall metrics
    if 'vowel' in df.columns and len(df['vowel'].unique()) >= 3:
        # Calculate area using vowel means
        vowel_means = df.groupby('vowel')[['F1', 'F2']].mean().reset_index()
        results['overall'] = calc_metrics(vowel_means)
    else:
        results['overall'] = calc_metrics(df)
    
    # Group-wise metrics
    if group_by and group_by in df.columns:
        results['by_group'] = {}
        
        for group in df[group_by].unique():
            group_data = df[df[group_by] == group]
            
            if 'vowel' in group_data.columns and len(group_data['vowel'].unique()) >= 3:
                vowel_means = group_data.groupby('vowel')[['F1', 'F2']].mean().reset_index()
                results['by_group'][str(group)] = calc_metrics(vowel_means)
            else:
                results['by_group'][str(group)] = calc_metrics(group_data)
    
    return results


def perform_comprehensive_analysis(df):
    """
    Perform comprehensive multivariate analysis
    
    Args:
        df: DataFrame with formant data
    
    Returns:
        dict with all analysis results
    """
    results = {
        'descriptive': {},
        'manova': {},
        'pca': {},
        'lda': {},
        'pairwise': {},
        'vowel_space': {}
    }
    
    # Determine grouping variables
    group_vars = []
    if 'vowel' in df.columns:
        group_vars.append('vowel')
    if 'speaker' in df.columns:
        group_vars.append('speaker')
    if 'native_language' in df.columns:
        group_vars.append('native_language')
    
    # Descriptive statistics
    for group_var in group_vars:
        results['descriptive'][group_var] = calculate_descriptive_statistics(df, group_by=group_var)
    
    # MANOVA
    for group_var in group_vars:
        results['manova'][group_var] = perform_manova(df, group_by=group_var)
    
    # PCA
    pca_results, df_pca = perform_pca(df)
    results['pca'] = pca_results
    results['pca_data'] = df_pca
    
    # LDA
    for group_var in group_vars:
        lda_results, df_lda = perform_lda(df, group_by=group_var)
        results['lda'][group_var] = lda_results
        results['lda_data_' + group_var] = df_lda
    
    # Pairwise tests
    for group_var in group_vars:
        results['pairwise'][group_var] = perform_pairwise_tests(df, group_by=group_var)
    
    # Vowel space metrics
    for group_var in group_vars:
        results['vowel_space'][group_var] = calculate_vowel_space_metrics(df, group_by=group_var)
    
    return results
