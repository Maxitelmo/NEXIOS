# build_nexios.spec
# PyInstaller spec — NEXIOS portable para Windows
# Uso: pyinstaller build_nexios.spec
# Salida: dist\NEXIOS_1.0.0\NEXIOS.exe

import os
from pathlib import Path

ROOT = Path(SPECPATH)

block_cipher = None

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Assets gráficos (agregar cuando existan)
        # (str(ROOT / 'assets' / 'Logo_NEXIOS.png'), 'assets'),
        # (str(ROOT / 'assets' / 'icono_nexios.ico'), 'assets'),
    ],
    hiddenimports=[
        # ── versión ──────────────────────────────────────────────────────────
        'version_nexios',

        # ── nexios core ──────────────────────────────────────────────────────
        'nexios',
        'nexios.core',
        'nexios.core.device_service',
        'nexios.core.acquisition_service',
        'nexios.core.screenshot_service',

        # ── nexios parsers ───────────────────────────────────────────────────
        'nexios.parsers',
        'nexios.parsers.ios',
        'nexios.parsers.ios.sms',
        'nexios.parsers.ios.contactos',
        'nexios.parsers.ios.llamadas',
        'nexios.parsers.ios.whatsapp',
        'nexios.parsers.ios.fotos',
        'nexios.parsers.ios.safari',
        'nexios.parsers.ios.notas',
        'nexios.parsers.ios.ubicaciones',
        'nexios.parsers.ios.calendario',
        'nexios.parsers.ios.recordatorios',
        'nexios.parsers.ios.telegram',
        'nexios.parsers.ios.grabaciones',
        'nexios.parsers.ios.voicemail',
        'nexios.parsers.ios.apps_instaladas',
        'nexios.parsers.ios.wifi',
        'nexios.parsers.ios.cuentas',
        'nexios.parsers.ios.fotos_eliminadas',
        'nexios.parsers.ios.uso_apps',
        'nexios.parsers.ios.bluetooth',

        # ── nexios modules ───────────────────────────────────────────────────
        'nexios.modules',
        'nexios.modules.fotos_operativo',

        # ── nexios utils ─────────────────────────────────────────────────────
        'nexios.utils',
        'nexios.utils.file_system',
        'nexios.utils.hash_utils',
        'nexios.utils.forensic_log_chain',
        'nexios.utils.integrity',

        # ── nexios pdf ───────────────────────────────────────────────────────
        'nexios.pdf',
        'nexios.pdf.report_generator',

        # ── nexios ui ────────────────────────────────────────────────────────
        'nexios.ui',
        'nexios.ui.main_window',
        'nexios.ui.device_panel',
        'nexios.ui.acquisition_panel',
        'nexios.ui.screenshot_panel',
        'nexios.ui.fotos_panel',

        # ── pymobiledevice3 (agregar según warnings de compilación) ──────────
        'pymobiledevice3',
        'pymobiledevice3.lockdown',
        'pymobiledevice3.usbmux',
        'pymobiledevice3.services.afc',
        'pymobiledevice3.services.screenshotr',
        'pymobiledevice3.services.installation_proxy',
        'pymobiledevice3.services.mobile_backup2',
        'pymobiledevice3.services.dvt.instruments.process_control',

        # ── stdlib / deps ────────────────────────────────────────────────────
        'sqlite3',
        'plistlib',
        'hashlib',
        'pathlib',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageOps',
        'PIL.ExifTags',
        'reportlab',
        'reportlab.lib',
        'reportlab.lib.pagesizes',
        'reportlab.lib.styles',
        'reportlab.lib.units',
        'reportlab.lib.colors',
        'reportlab.platypus',
        'reportlab.platypus.tables',
        'reportlab.platypus.flowables',
        'reportlab.graphics',
        'customtkinter',
        'jinja2',
        'jinja2.ext',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NEXIOS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                          # Sin consola (app GUI)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=str(ROOT / 'assets' / 'icono_nexios.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NEXIOS_1.0.0',
)
