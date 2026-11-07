"""
Quick checks for utils/formant_ceiling.py using the WAV/TextGrid pairs in test/.

Run:  .venv/bin/python test_formant_ceiling.py
"""
import glob
import sys
import time

import numpy as np
import parselmouth

sys.path.insert(0, '.')
from utils.data_processor import collect_vowel_tokens, process_wav_textgrid  # noqa: E402
from utils.formant_ceiling import (build_sweep_sound, f1f2_score, f3f4_score,  # noqa: E402
                                   measure_tokens, optimize_ceiling)


def test_scores():
    F = np.array([[500, 1500, 2500, 3500], [510, 1520, 2510, 3490], [700, 1200, 2490, 3510]], float)
    assert f3f4_score(F) < 0.1
    assert f1f2_score(F, ['a', 'a', 'o']) is not None
    assert f1f2_score(F, ['a', 'o', 'i']) is None          # no repeated vowel -> fallback
    F[:, 3] = np.nan
    assert f3f4_score(F) == np.inf                          # missing F4 -> rejected
    print('scores ok')


def test_sweep_sound_matches_full():
    wav = 'test/mv01_t01_s04.wav'
    sound = parselmouth.Sound(wav)
    tokens = collect_vowel_tokens(parselmouth.read(wav.replace('.wav', '.TextGrid')))
    short, remapped = build_sweep_sound(sound, tokens)
    assert len(remapped) == len(tokens)
    assert short.duration < sound.duration
    full = measure_tokens(sound, tokens, 5000)
    part = measure_tokens(short, remapped, 5000)
    ok = ~np.isnan(full) & ~np.isnan(part)
    rel = np.abs(full[ok] - part[ok]) / full[ok]
    print(f'sweep sound: {sound.duration:.1f}s -> {short.duration:.1f}s, '
          f'median |diff| {np.median(rel)*100:.2f}%, 95th pct {np.percentile(rel,95)*100:.2f}%')
    assert np.median(rel) < 0.02


def test_optimize_per_speaker():
    for wav, lo, hi in [('test/fv01_t01_s01.wav', 5000, 6500), ('test/mv01_t01_s04.wav', 4300, 5300)]:
        sound = parselmouth.Sound(wav)
        tokens = collect_vowel_tokens(parselmouth.read(wav.replace('.wav', '.TextGrid')))
        t0 = time.time()
        r = optimize_ceiling([(sound, tokens)], criterion='f3f4')
        print(f'{wav}: ceiling {r["ceiling"]:.0f} Hz ({r["criterion"]}, {r["n_tokens"]} tokens, {time.time()-t0:.1f}s)')
        assert lo <= r['ceiling'] <= hi, r


def test_pipeline_reduces_within_vowel_spread():
    wavs = sorted(glob.glob('test/mv01*.wav'))
    tgs = [w.replace('.wav', '.TextGrid') for w in wavs]
    fixed, _ = process_wav_textgrid(wavs, tgs, ceiling_mode='fixed', fixed_ceiling=5500)
    auto, meta = process_wav_textgrid(wavs, tgs, ceiling_mode='auto', ceiling_criterion='f3f4')
    assert {'F3', 'F4', 'formant_ceiling'} <= set(auto.columns)

    def pooled_sd(df):
        g = df.groupby('vowel')
        big = [v for v, d in g if len(d) >= 5]
        return np.mean([np.log(g.get_group(v)[['F1', 'F2']]).std().mean() for v in big])
    sf, sa = pooled_sd(fixed), pooled_sd(auto)
    print(f'pooled within-vowel log-SD: fixed 5500 Hz {sf:.3f} -> auto {sa:.3f} '
          f'(ceiling {meta["formant_ceiling"]["speakers"]["mv01"]["ceiling"]:.0f} Hz)')
    assert sa <= sf


def test_per_vowel_scope():
    wavs = sorted(glob.glob('test/mv01*.wav'))
    items = [(parselmouth.Sound(w), collect_vowel_tokens(parselmouth.read(w.replace('.wav', '.TextGrid'))))
             for w in wavs]
    r = optimize_ceiling(items, criterion='f1f2', scope='vowel')
    assert 'vowels' in r and r['vowels']
    for v, vr in r['vowels'].items():
        if vr['criterion']:                       # optimised vowel
            assert vr['n_tokens'] >= 5
            assert 0.8 * r['ceiling'] - 1 <= vr['ceiling'] <= 1.25 * r['ceiling'] + 1, (v, vr)
        else:                                     # fell back to speaker ceiling
            assert vr['ceiling'] == r['ceiling']
    own = {v: int(vr['ceiling']) for v, vr in r['vowels'].items() if vr['criterion']}
    print(f'per-vowel (speaker {r["ceiling"]:.0f} Hz): {own}')

    tgs = [w.replace('.wav', '.TextGrid') for w in wavs]
    df, meta = process_wav_textgrid(wavs, tgs, ceiling_mode='auto', ceiling_criterion='f1f2',
                                    ceiling_scope='vowel')
    used = df.groupby('vowel')['formant_ceiling'].nunique()
    assert (used == 1).all(), used                 # one ceiling per vowel category
    assert meta['formant_ceiling']['scope'] == 'vowel'
    for v, c in own.items():
        assert int(df[df['vowel'] == v]['formant_ceiling'].iloc[0]) == c, v


if __name__ == '__main__':
    test_scores()
    test_sweep_sound_matches_full()
    test_optimize_per_speaker()
    test_pipeline_reduces_within_vowel_spread()
    test_per_vowel_scope()
    print('all ok')
