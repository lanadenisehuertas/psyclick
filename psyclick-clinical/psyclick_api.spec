# psyclick_api.spec — PyInstaller build spec for PsyClick Clinical Edition API
# Run: pyinstaller psyclick_api.spec --noconfirm --distpath dist-python
import os
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

# Always resolve relative to this spec file so it works regardless of cwd
SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))

numpy_hidden = [m for m in collect_submodules('numpy.fft') if '.tests' not in m]
scipy_hidden = [m for m in collect_submodules('scipy.stats') if '.tests' not in m]
pandas_hidden = [
    'pandas._libs.tslibs.np_datetime',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.timezones',
]

numpy_bins = collect_dynamic_libs('numpy')
scipy_bins = collect_dynamic_libs('scipy')
pandas_bins = collect_dynamic_libs('pandas')

a = Analysis(
    [os.path.join(SPEC_DIR, 'api_server.py')],
    pathex=[SPEC_DIR],
    binaries=numpy_bins + scipy_bins + pandas_bins,
    datas=[
        (os.path.join(SPEC_DIR, 'images', 'LOGOggg.png'), 'images'),
        (os.path.join(SPEC_DIR, 'images', 'LOGO WITH WORD.png'), 'images'),
        (os.path.join(SPEC_DIR, 'images', 'LOGO WITH WORD white.png'), 'images'),
        (os.path.join(SPEC_DIR, 'images', 'LOGO white.png'), 'images'),
        (os.path.join(SPEC_DIR, 'images', 'WORD.png'), 'images'),
        (os.path.join(SPEC_DIR, 'images', 'WORD_.png'), 'images'),
        (os.path.join(SPEC_DIR, 'database_manager.py'), '.'),
        (os.path.join(SPEC_DIR, 'backend_controller.py'), '.'),
        (os.path.join(SPEC_DIR, 'dynamics_logger.py'), '.'),
        (os.path.join(SPEC_DIR, 'feature_extractor.py'), '.'),
        (os.path.join(SPEC_DIR, 'anomaly_engine.py'), '.'),
        (os.path.join(SPEC_DIR, 'report_exporter.py'), '.'),
        (os.path.join(SPEC_DIR, 'supabase_sync.py'), '.'),
        (os.path.join(SPEC_DIR, 'security_manager.py'), '.'),
    ],
    hiddenimports=[
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'pynput._util.win32',
        'six',
        'scipy.stats',
        'scipy.special',
        'scipy.special._ufuncs_cxx',
        'scipy._lib.messagestream',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.timezones',
        'psycopg2',
        'psycopg2.extensions',
        'psycopg2._psycopg',
        'backend_controller',
        'database_manager',
        'dynamics_logger',
        'feature_extractor',
        'anomaly_engine',
        'report_exporter',
        'supabase_sync',
        'security_manager',
        # supabase-py (optional — gracefully skipped if absent)
        'supabase',
        'httpx',
        'httpcore',
        'gotrue',
        'postgrest',
        'realtime',
        'storage3',
    ] + numpy_hidden + scipy_hidden + pandas_hidden,
    excludes=[
        'interactions',
        'customtkinter',
        'tkinter',
        '_tkinter',
        'matplotlib',
        'PIL',
        'PyQt5',
        'PySide2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='psyclick_api',
    debug=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='psyclick_api',
)
