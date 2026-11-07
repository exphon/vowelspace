"""
Per-speaker formant ceiling optimization.

Praat's default formant ceiling is fixed by sex (5000 Hz men / 5500 Hz women).
A ceiling that does not match the speaker's vocal tract makes the LPC tracker
merge or split formants, which shows up as implausible F1/F2 values.

This module sweeps a range of ceilings and picks the one that gives the most
stable formant measurements for a speaker, following two published criteria:

* ``f1f2`` - Escudero, Boersma, Rauber & Bion (2009, JASA): minimise the
  within-vowel variance of 20*log10(F1) and 20*log10(F2). Needs repeated
  tokens of the same vowel.
* ``f3f4`` - Feinberg (2019, OSF preregistration PDWCB): minimise the
  across-token variance of 20*log10(F3) and 20*log10(F4). F3/F4 vary less
  across vowels than F1/F2, so this works even with one token per vowel.
* ``combined`` - sum of the two (both are in dB^2 units).

The sweep is coarse-to-fine: 100 Hz steps across the full range, then 20 Hz
steps around the best coarse ceiling.
"""
import warnings

import numpy as np

try:
    import parselmouth
    from parselmouth.praat import call
except ImportError:  # pragma: no cover - handled by caller
    parselmouth = None
    call = None

DEFAULT_MIN_CEILING = 4000.0
DEFAULT_MAX_CEILING = 8000.0
COARSE_STEP = 100.0
FINE_STEP = 20.0

# Praat analysis settings shared by the sweep and the final extraction
TIME_STEP = 0.01
MAX_N_FORMANTS = 5
WINDOW_LENGTH = 0.025
PRE_EMPHASIS = 50.0

# A ceiling is rejected if more than this fraction of tokens lack F3/F4
MAX_MISSING_FRACTION = 0.2

CRITERIA = ('f3f4', 'f1f2', 'combined')


def compute_formant(sound, ceiling):
    """Run Praat's Burg formant analysis with the shared settings."""
    return sound.to_formant_burg(
        time_step=TIME_STEP,
        max_number_of_formants=MAX_N_FORMANTS,
        maximum_formant=float(ceiling),
        window_length=WINDOW_LENGTH,
        pre_emphasis_from=PRE_EMPHASIS,
    )


def token_time_points(start, end, n_points=5, min_duration=0.02):
    """
    Time points at which a vowel token is measured.

    Tokens longer than ``min_duration`` are sampled at ``n_points`` points in
    the middle 25% (37.5%-62.5%) of their duration; shorter ones at the
    midpoint only.
    """
    duration = end - start
    if duration > min_duration:
        return np.linspace(start + duration * 0.375, start + duration * 0.625, n_points)
    return np.array([(start + end) / 2.0])


def measure_token(formant, start, end, n_formants=4):
    """
    Average F1..Fn of one token over its measurement points.

    Returns a float array of length ``n_formants`` (NaN where Praat found no
    formant).
    """
    points = token_time_points(start, end)
    values = np.full((len(points), n_formants), np.nan)
    for i, t in enumerate(points):
        for k in range(n_formants):
            v = call(formant, "Get value at time", k + 1, float(t), "hertz", "linear")
            if v is not None and not np.isnan(v):
                values[i, k] = v
    if not len(points):
        return np.full(n_formants, np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)  # all-NaN columns -> NaN
        return np.nanmean(values, axis=0)


def measure_tokens(sound, tokens, ceiling):
    """
    Measure every token of one sound at the given ceiling.

    ``tokens`` is a list of dicts with ``start`` and ``end`` (seconds).
    Returns an (n_tokens x 4) array of F1..F4 means.
    """
    formant = compute_formant(sound, ceiling)
    out = np.full((len(tokens), 4), np.nan)
    for i, tok in enumerate(tokens):
        out[i] = measure_token(formant, tok['start'], tok['end'])
    return out


# Sweep speed-up: only the vowel tokens (plus padding) are analysed, and at
# most this many tokens per speaker are used to pick the ceiling.
SWEEP_PADDING = 0.05
MAX_SWEEP_TOKENS = 1500
MAX_SWEEP_SECONDS = 30.0   # max token audio (per speaker) analysed per ceiling


def subsample_tokens(items, max_tokens=MAX_SWEEP_TOKENS, max_seconds=MAX_SWEEP_SECONDS,
                     padding=SWEEP_PADDING):
    """
    Keep an evenly spaced subset of tokens so that the sweep stays fast:
    at most ``max_tokens`` tokens and about ``max_seconds`` of (padded) audio.
    """
    flat = [(i, tok) for i, (_, toks) in enumerate(items) for tok in toks]
    n = len(flat)
    if n == 0:
        return items
    total = sum(tok['end'] - tok['start'] + 2 * padding for _, tok in flat)
    frac = min(1.0, max_tokens / n, max_seconds / total if total > 0 else 1.0)
    if frac >= 1.0:
        return items
    keep = set(np.unique(np.linspace(0, n - 1, max(2, int(round(n * frac)))).astype(int)))
    kept = [[] for _ in items]
    for j, (i, tok) in enumerate(flat):
        if j in keep:
            kept[i].append(tok)
    return [(sound, toks) for (sound, _), toks in zip(items, kept)]


def build_sweep_sound(sound, tokens, padding=SWEEP_PADDING):
    """
    Concatenate the token regions of ``sound`` (each padded by ``padding``
    seconds) into one shorter Sound, and return it with the tokens remapped
    to the new time axis. Running the ceiling sweep on this sound instead of
    the full recording skips silence and consonants.
    """
    if not tokens:
        return sound, []
    # Merge overlapping padded regions so no audio is duplicated
    regions = sorted((max(0.0, t['start'] - padding), min(sound.duration, t['end'] + padding))
                     for t in tokens)
    merged = [list(regions[0])]
    for a, b in regions[1:]:
        if a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    if sum(b - a for a, b in merged) >= 0.9 * sound.duration:
        return sound, list(tokens)

    parts, offsets, cursor = [], [], 0.0
    for a, b in merged:
        part = sound.extract_part(from_time=a, to_time=b, preserve_times=False)
        parts.append(part)
        offsets.append((a, b, cursor))
        cursor += part.duration
    new_sound = parselmouth.Sound.concatenate(parts)

    remapped = []
    for t in tokens:
        for a, b, off in offsets:
            if a <= t['start'] and t['end'] <= b:
                nt = dict(t)
                nt['start'] = t['start'] - a + off
                nt['end'] = t['end'] - a + off
                remapped.append(nt)
                break
    return new_sound, remapped


def _db(x):
    return 20.0 * np.log10(x)


def f3f4_score(F):
    """Across-token variance of 20log10(F3) + 20log10(F4)."""
    f3, f4 = F[:, 2], F[:, 3]
    ok = ~(np.isnan(f3) | np.isnan(f4))
    if ok.sum() < 2:
        return np.inf
    if 1.0 - ok.mean() > MAX_MISSING_FRACTION:
        return np.inf
    return float(np.var(_db(f3[ok])) + np.var(_db(f4[ok])))


def f1f2_score(F, labels):
    """
    Pooled within-vowel variance of 20log10(F1) + 20log10(F2).

    Only vowels with at least two tokens contribute. Returns None when no
    vowel is repeated, so the caller can fall back to another criterion.
    """
    labels = np.asarray(labels)
    f1, f2 = F[:, 0], F[:, 1]
    ok = ~(np.isnan(f1) | np.isnan(f2))
    if ok.sum() < 2:
        return np.inf
    if 1.0 - ok.mean() > MAX_MISSING_FRACTION:
        return np.inf
    ss = 0.0
    dof = 0
    for v in np.unique(labels[ok]):
        m = ok & (labels == v)
        if m.sum() < 2:
            continue
        ss += float(np.sum((_db(f1[m]) - _db(f1[m]).mean()) ** 2))
        ss += float(np.sum((_db(f2[m]) - _db(f2[m]).mean()) ** 2))
        dof += m.sum() - 1
    if dof == 0:
        return None
    return ss / dof


def has_repeated_vowels(labels, min_repeats=2):
    labels = [l for l in labels if l and l != 'unlabeled']
    if not labels:
        return False
    _, counts = np.unique(np.asarray(labels), return_counts=True)
    return bool((counts >= min_repeats).any())


# Plausibility limits (Fast Track heuristics, Barreda 2021): a ceiling whose
# measurements violate these is rejected even if its variance is low, because
# low variance can also come from consistently merged/mislabelled formants.
MAX_MEDIAN_F1 = 1200.0
MIN_MEDIAN_F4 = 2900.0
MAX_MERGED_FRACTION = 0.2   # tokens with F2 - F1 < MIN_F2_F1_GAP
MIN_F2_F1_GAP = 150.0


def implausible(F):
    """True when the measurements at this ceiling look like tracking failures."""
    f1, f2, f4 = F[:, 0], F[:, 1], F[:, 3]
    ok12 = ~(np.isnan(f1) | np.isnan(f2))
    if ok12.sum() == 0:
        return True
    if np.median(f1[ok12]) > MAX_MEDIAN_F1:
        return True
    if np.mean((f2[ok12] - f1[ok12]) < MIN_F2_F1_GAP) > MAX_MERGED_FRACTION:
        return True
    ok4 = ~np.isnan(f4)
    if ok4.any() and np.median(f4[ok4]) < MIN_MEDIAN_F4:
        return True
    return False


def score_measurements(F, labels, criterion):
    """
    Score one ceiling. Lower is better.

    Returns (score, criterion_actually_used). ``f1f2``/``combined`` fall back
    to ``f3f4`` when no vowel is repeated. Implausible ceilings score inf.
    """
    if implausible(F):
        used = 'f3f4' if criterion == 'f3f4' or f1f2_score(F, labels) is None else criterion
        return np.inf, used
    if criterion == 'f3f4':
        return f3f4_score(F), 'f3f4'
    s12 = f1f2_score(F, labels)
    if s12 is None:
        return f3f4_score(F), 'f3f4'
    if criterion == 'f1f2':
        return s12, 'f1f2'
    return s12 + f3f4_score(F), 'combined'


def _smooth3(values):
    """3-point moving average; infinities propagate so bad ceilings stay bad."""
    v = np.asarray(values, dtype=float)
    if len(v) < 3:
        return v
    out = v.copy()
    out[1:-1] = (v[:-2] + v[1:-1] + v[2:]) / 3.0
    return out


MIN_TOKENS_PER_VOWEL = 5   # per-vowel optimisation needs at least this many tokens
# Per-vowel ceilings are searched within this factor range of the speaker
# ceiling (about -20%/+25%, the span of Praat's FormantPath default of
# 4 steps of 5% up and down). Escudero et al. (2009) found about +-10-15%
# between vowels of one speaker.
VOWEL_WINDOW = (0.8, 1.25)
SCOPES = ('speaker', 'vowel')


class _Sweep:
    """
    Coarse-to-fine ceiling search over a set of (sound, tokens) items with a
    per-ceiling measurement cache, so that per-vowel searches can reuse the
    coarse pass made for the whole speaker.
    """

    def __init__(self, items, criterion, min_ceiling, max_ceiling, coarse_step, fine_step):
        self.items = items
        self.labels = np.asarray([tok.get('vowel') or 'unlabeled' for _, toks in items for tok in toks])
        self.criterion = criterion
        self.min_ceiling, self.max_ceiling = min_ceiling, max_ceiling
        self.coarse_step, self.fine_step = coarse_step, fine_step
        self.cache = {}          # ceiling -> (n_tokens x 4) F1..F4
        self.used_criterion = criterion

    def measure(self, ceiling):
        ceiling = float(round(ceiling))
        if ceiling not in self.cache:
            self.cache[ceiling] = np.vstack([measure_tokens(sound, toks, ceiling)
                                             for sound, toks in self.items])
        return self.cache[ceiling]

    def score(self, ceiling, mask=None):
        F = self.measure(ceiling)
        labels = self.labels
        if mask is not None:
            F, labels = F[mask], labels[mask]
        score, used = score_measurements(F, labels, self.criterion)
        self.used_criterion = used
        return score

    def coarse_grid(self, lo=None, hi=None):
        lo = self.min_ceiling if lo is None else max(lo, self.min_ceiling)
        hi = self.max_ceiling if hi is None else min(hi, self.max_ceiling)
        grid = np.arange(self.min_ceiling, self.max_ceiling + 0.5, self.coarse_step)
        return grid[(grid >= lo - 1e-6) & (grid <= hi + 1e-6)]

    def best_coarse(self, mask=None, lo=None, hi=None):
        grid = self.coarse_grid(lo, hi)
        if len(grid) == 0:
            return None, np.array([])
        scores = np.array([self.score(c, mask) for c in grid])
        if not np.isfinite(scores).any():
            return None, scores
        return float(grid[int(np.argmin(_smooth3(scores)))]), scores

    def fine_candidates(self, best_coarse, lo=None, hi=None):
        lo = self.min_ceiling if lo is None else max(lo, self.min_ceiling)
        hi = self.max_ceiling if hi is None else min(hi, self.max_ceiling)
        fine = np.arange(best_coarse - self.coarse_step, best_coarse + self.coarse_step + 0.5, self.fine_step)
        return fine[(fine >= lo - 1e-6) & (fine <= hi + 1e-6)]

    def sweep_list(self, mask=None):
        out = []
        for c in sorted(self.cache):
            s = self.score(c, mask)
            out.append([float(c), None if not np.isfinite(s) else round(float(s), 4)])
        return out


def _finish(sweep, best_coarse, scorer, n_tokens, sweep_list, lo=None, hi=None):
    """Fine search around ``best_coarse`` using ``scorer(ceiling)``; returns result dict."""
    candidates = {}
    for c in sweep.fine_candidates(best_coarse, lo, hi):
        s = scorer(c)
        if np.isfinite(s):
            candidates[float(round(c))] = s
    if not candidates:
        return None
    best = min(candidates, key=candidates.get)
    return {
        'ceiling': float(best),
        'criterion': sweep.used_criterion,
        'score': round(float(candidates[best]), 4),
        'n_tokens': int(n_tokens),
        'sweep': sweep_list,
    }


def optimize_ceiling(items, criterion='f3f4', scope='speaker',
                     min_ceiling=DEFAULT_MIN_CEILING, max_ceiling=DEFAULT_MAX_CEILING,
                     coarse_step=COARSE_STEP, fine_step=FINE_STEP, fallback=5500.0,
                     min_tokens_per_vowel=MIN_TOKENS_PER_VOWEL):
    """
    Find the formant ceiling that gives the most stable formants for a speaker.

    Args:
        items: list of (sound, tokens) pairs - all recordings of one speaker.
               ``tokens`` is a list of dicts with ``start``, ``end``, ``vowel``.
        criterion: 'f3f4', 'f1f2' or 'combined'.
        scope: 'speaker' gives one ceiling per speaker. 'vowel' additionally
               optimises a separate ceiling for every vowel category with at
               least ``min_tokens_per_vowel`` tokens (Escudero et al. 2009),
               searched within ``VOWEL_WINDOW`` times the speaker ceiling;
               other vowels keep the speaker ceiling.
        fallback: ceiling returned when no ceiling could be scored.

    Returns a dict with ``ceiling``, ``criterion`` (the one actually used),
    ``score``, ``n_tokens``, ``sweep`` (list of [ceiling, score]) and, for
    scope 'vowel', ``vowels``: {vowel: {ceiling, criterion, score, n_tokens,
    note}}.
    """
    if criterion not in CRITERIA:
        raise ValueError(f"Unknown criterion {criterion!r}; expected one of {CRITERIA}")
    if scope not in SCOPES:
        raise ValueError(f"Unknown scope {scope!r}; expected one of {SCOPES}")

    items = [(s, t) for s, t in items if t]
    n_tokens = sum(len(t) for _, t in items)
    if n_tokens < 2:
        return {'ceiling': float(fallback), 'criterion': None, 'score': None,
                'n_tokens': n_tokens, 'sweep': [], 'note': 'too few tokens; fixed ceiling used'}

    # Cap the amount of audio used for the sweep, then analyse only the
    # (padded) token regions
    items = subsample_tokens(items)
    sweep_items = [build_sweep_sound(sound, toks) for sound, toks in items]
    sweep_items = [(s, t) for s, t in sweep_items if t]
    sweep = _Sweep(sweep_items, criterion, min_ceiling, max_ceiling, coarse_step, fine_step)

    # ---- speaker-level ceiling ----
    best_coarse, _ = sweep.best_coarse()
    result = None
    if best_coarse is not None:
        result = _finish(sweep, best_coarse, lambda c: sweep.score(c), n_tokens, None)
    if result is None:
        result = {'ceiling': float(fallback), 'criterion': sweep.used_criterion, 'score': None,
                  'n_tokens': n_tokens, 'sweep': sweep.sweep_list(),
                  'note': 'no ceiling produced stable F1-F4; fixed ceiling used'}
    else:
        result['sweep'] = sweep.sweep_list()
    if scope != 'vowel':
        return result

    # ---- per-vowel ceilings (Escudero et al. 2009), reusing the coarse pass ----
    result['vowels'] = {}
    vowels, counts = np.unique(sweep.labels, return_counts=True)
    for vowel, count in zip(vowels, counts):
        if vowel == 'unlabeled':
            continue
        if count < min_tokens_per_vowel:
            result['vowels'][str(vowel)] = {
                'ceiling': result['ceiling'], 'criterion': None, 'score': None,
                'n_tokens': int(count),
                'note': f'fewer than {min_tokens_per_vowel} tokens; speaker ceiling used'}
            continue
        mask = sweep.labels == vowel
        lo, hi = result['ceiling'] * VOWEL_WINDOW[0], result['ceiling'] * VOWEL_WINDOW[1]
        v_coarse, _ = sweep.best_coarse(mask, lo, hi)
        v_result = None
        if v_coarse is not None:
            # Fine search on a sweep sound that contains only this vowel's
            # tokens, so each extra analysis costs only that vowel's audio.
            v_items = [build_sweep_sound(sound, [t for t in toks if (t.get('vowel') or 'unlabeled') == vowel])
                       for sound, toks in items]
            v_items = [(s, t) for s, t in v_items if t]
            v_sweep = _Sweep(v_items, criterion, min_ceiling, max_ceiling, coarse_step, fine_step)
            v_result = _finish(v_sweep, v_coarse, lambda c: v_sweep.score(c), count, None, lo, hi)
            if v_result is not None:
                v_result['sweep'] = v_sweep.sweep_list()
        if v_result is None:
            v_result = {'ceiling': result['ceiling'], 'criterion': None, 'score': None,
                        'n_tokens': int(count), 'sweep': [],
                        'note': 'no stable ceiling for this vowel; speaker ceiling used'}
        result['vowels'][str(vowel)] = v_result
    return result
