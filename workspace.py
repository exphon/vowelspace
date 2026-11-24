"""
Per-user storage for uploaded files.

Each user has one private folder, ``uploads/user<ID>/``:

    files/    every file the user has uploaded; new uploads are added to it
              (a file with the same name is replaced), so data sets uploaded
              at different times can be plotted together. Files stay until
              the user deletes them, one by one or all at once
    cache/    results derived from those files (formant measurements, the
              CSV offered for download); removed together with the files

Nothing is shared between users and uploads never overwrite each other.
Folders that have not been used for ``UPLOAD_RETENTION_DAYS`` (default 7)
are removed automatically, so abandoned recordings do not stay on the server.
"""
import fcntl
import hashlib
import json
import os
import re
import shutil
import time
import unicodedata
from contextlib import contextmanager

import pandas as pd

RETENTION_DAYS = float(os.environ.get('UPLOAD_RETENTION_DAYS', '7'))
_USER_DIR = re.compile(r'^user\d+$')


def safe_filename(name):
    """
    File name without any path part or unsafe characters.

    Unlike werkzeug's ``secure_filename`` this keeps non-ASCII letters, so
    Korean file names survive and WAV/TextGrid pairs still match by name.
    """
    name = unicodedata.normalize('NFC', str(name or ''))
    name = name.replace('\\', '/').rsplit('/', 1)[-1]
    name = re.sub(r'[^\w.\- ]', '_', name).strip(' .')
    return name[:200]


class Workspace:
    """The storage folder of one user."""

    def __init__(self, upload_root, user_id):
        self.root = os.path.join(upload_root, f'user{int(user_id)}')
        self.files_dir = os.path.join(self.root, 'files')
        self.cache_dir = os.path.join(self.root, 'cache')

    @contextmanager
    def locked(self):
        """Serialize requests of one user (upload, re-plot and delete never interleave)."""
        os.makedirs(self.root, exist_ok=True)
        with open(os.path.join(self.root, '.lock'), 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield self
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def touch(self):
        """Mark the folder as recently used (resets the retention clock)."""
        if os.path.isdir(self.root):
            os.utime(self.root, None)

    # -- uploaded files ----------------------------------------------------
    # -- upload sets --------------------------------------------------------
    # Every upload is one "set" (numbered 1, 2, ... with an optional label), so
    # files added later can be compared with the ones uploaded before.
    def _sets_path(self):
        return os.path.join(self.root, 'sets.json')

    def _load_sets(self):
        try:
            with open(self._sets_path()) as f:
                sets = json.load(f)
        except (OSError, ValueError):
            sets = {}
        sets.setdefault('files', {})
        sets.setdefault('labels', {})
        return sets

    def _save_sets(self, sets):
        with open(self._sets_path(), 'w') as f:
            json.dump(sets, f, ensure_ascii=False)

    def file_sets(self):
        """``{file name: (set number, set label)}`` for every stored file."""
        sets = self._load_sets()
        result = {}
        for f in self.files():
            number = sets['files'].get(f['name'], 1)   # files from before sets existed
            result[f['name']] = (number, sets['labels'].get(str(number)) or f'Set {number}')
        return result

    def add_files(self, uploads, allowed, check=None, label=None):
        """
        Add ``uploads`` (werkzeug FileStorage objects) to the stored files.
        They form a new upload set, named ``label`` if given.

        A file with the same name as a stored one replaces it. The new files
        are written to a side folder first; ``check(files)`` is then called
        with the set as it would be afterwards (dicts with name, ext, size)
        and may raise to reject the upload, in which case the stored files
        stay untouched. Returns the number of files saved.
        """
        incoming = os.path.join(self.root, 'incoming')
        shutil.rmtree(incoming, ignore_errors=True)
        os.makedirs(incoming)
        saved = 0
        try:
            for upload in uploads:
                name = safe_filename(upload.filename)
                if not name or not allowed(name):
                    continue
                upload.save(os.path.join(incoming, name))
                saved += 1
            if saved:
                new_names = set(os.listdir(incoming))
                if check:
                    after = [f for f in self.files() if f['name'] not in new_names]
                    after += self._describe(incoming)
                    check(sorted(after, key=lambda f: f['name']))
                os.makedirs(self.files_dir, exist_ok=True)
                sets = self._load_sets()
                kept = {f['name'] for f in self.files()} - new_names
                # files stored before sets existed count as set 1
                numbers = {name: sets['files'].get(name, 1) for name in kept}
                number = max(numbers.values(), default=0) + 1
                for name in new_names:
                    os.replace(os.path.join(incoming, name), os.path.join(self.files_dir, name))
                    numbers[name] = number
                used = {str(n) for n in numbers.values()}
                labels = {n: text for n, text in sets['labels'].items() if n in used and n != str(number)}
                label = re.sub(r'\s+', ' ', str(label or '')).strip()[:40]
                if label:
                    labels[str(number)] = label
                self._save_sets({'files': numbers, 'labels': labels})
                shutil.rmtree(self.cache_dir, ignore_errors=True)   # measurements depend on the file set
        finally:
            shutil.rmtree(incoming, ignore_errors=True)
        return saved

    def delete_files(self, names):
        """Remove the stored files with these names. Returns the number removed."""
        wanted = {safe_filename(n) for n in names}
        removed = 0
        for f in self.files():
            if f['name'] in wanted:
                os.remove(f['path'])
                removed += 1
        if removed:
            shutil.rmtree(self.cache_dir, ignore_errors=True)
        return removed

    @staticmethod
    def _describe(folder):
        result = []
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if os.path.isfile(path) and '.' in name:
                result.append({
                    'name': name,
                    'path': path,
                    'ext': name.rsplit('.', 1)[1].lower(),
                    'size': os.path.getsize(path),
                })
        return result

    def files(self):
        """Stored files as dicts with name, path, ext (lower-case) and size."""
        if not os.path.isdir(self.files_dir):
            return []
        return self._describe(self.files_dir)

    def listing(self):
        """Names and sizes for the browser (no server paths)."""
        files = self.files()
        sets = self.file_sets()
        return {
            'files': [{'name': f['name'], 'size': f['size'],
                       'set': sets[f['name']][0], 'set_label': sets[f['name']][1]} for f in files],
            'set_count': len({number for number, _ in sets.values()}),
            'count': len(files),
            'total_size': sum(f['size'] for f in files),
            'retention_days': RETENTION_DAYS,
        }

    def delete(self):
        """Remove every stored and derived file of this user."""
        shutil.rmtree(self.files_dir, ignore_errors=True)
        shutil.rmtree(self.cache_dir, ignore_errors=True)
        shutil.rmtree(os.path.join(self.root, 'incoming'), ignore_errors=True)
        if os.path.exists(self._sets_path()):
            os.remove(self._sets_path())

    # -- derived results ---------------------------------------------------
    def cache_path(self, name):
        os.makedirs(self.cache_dir, exist_ok=True)
        return os.path.join(self.cache_dir, name)

    def _measurement_paths(self, options):
        key = hashlib.sha1(json.dumps(options, sort_keys=True).encode()).hexdigest()[:16]
        return self.cache_path(f'formants_{key}.pkl'), self.cache_path(f'formants_{key}.json')

    def load_measurements(self, options):
        """Cached (data, metadata) for these extraction options, or None."""
        data_path, meta_path = self._measurement_paths(options)
        if not (os.path.exists(data_path) and os.path.exists(meta_path)):
            return None
        try:
            with open(meta_path) as f:
                metadata = json.load(f)
            return pd.read_pickle(data_path), metadata
        except Exception:
            return None

    def save_measurements(self, options, data, metadata):
        data_path, meta_path = self._measurement_paths(options)
        try:
            with open(meta_path, 'w') as f:
                json.dump(metadata, f)
            data.to_pickle(data_path)
        except Exception as exc:   # the cache is an optimisation only
            print(f'Could not cache formant measurements: {exc}')
            for path in (data_path, meta_path):
                if os.path.exists(path):
                    os.remove(path)


def purge_expired(upload_root, now=None):
    """Delete user folders that were last used more than RETENTION_DAYS ago."""
    if RETENTION_DAYS <= 0 or not os.path.isdir(upload_root):
        return 0
    cutoff = (now or time.time()) - RETENTION_DAYS * 86400
    removed = 0
    for name in os.listdir(upload_root):
        path = os.path.join(upload_root, name)
        if _USER_DIR.match(name) and os.path.isdir(path) and os.path.getmtime(path) < cutoff:
            shutil.rmtree(path, ignore_errors=True)
            removed += 1
    return removed
