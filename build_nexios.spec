# build_nexios.spec
# PyInstaller spec — NEXIOS portable para Windows
# Uso: pyinstaller build_nexios.spec
# Salida: dist\NEXIOS_1.0.0\NEXIOS.exe

import os
import sys
from pathlib import Path

ROOT = Path(SPECPATH)

block_cipher = None

# ── Data files ──────────────────────────────────────────────────────────────────
import customtkinter as _ctk
CTK_DIR = Path(_ctk.__file__).parent

datas = [
    # Logo e iconos NEXIOS
    (str(ROOT / 'media' / 'NEXIOS-LOGO.png'), 'media'),
    # Temas y assets de CustomTkinter
    (str(CTK_DIR / 'assets'), 'customtkinter/assets'),
]

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
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

        # ── pymobiledevice3 ──────────────────────────────────────────────────
        'pymobiledevice3',
        'pymobiledevice3.lockdown',
        'pymobiledevice3.lockdown_service_provider',
        'pymobiledevice3.lockdown_service',          # no existe como módulo raíz
        'pymobiledevice3.usbmux',
        'pymobiledevice3.pair_records',
        'pymobiledevice3.exceptions',
        'pymobiledevice3.service_connection',
        'pymobiledevice3.services.afc',
        'pymobiledevice3.services.screenshot',
        'pymobiledevice3.services.mobilebackup2',
        'pymobiledevice3.services.installation_proxy',
        'pymobiledevice3.services.lockdown_service',
        'pymobiledevice3.services.heartbeat',
        'pymobiledevice3.services.amfi',
        'pymobiledevice3.remote',
        'pymobiledevice3.remote.common',
        'pymobiledevice3.remote.tunnel_service',
        'pymobiledevice3.remote.remote_service_discovery',
        'pymobiledevice3.remote.remotexpc',
        'pymobiledevice3.remote.utils',
        'pymobiledevice3.bonjour',

        # ── stdlib / deps ────────────────────────────────────────────────────
        'sqlite3',
        'plistlib',
        'hashlib',
        'pathlib',
        'asyncio',
        'threading',
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy', 'IPython', 'notebook'],
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=str(ROOT / 'media' / 'icono_nexios.ico'),  # habilitar cuando exista .ico
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
