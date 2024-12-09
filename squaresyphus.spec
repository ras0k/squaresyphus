# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/boulder_gray.png', 'assets'),
        ('assets/boulder_orange.png', 'assets'),
        ('assets/Clouds-Sheet.png', 'assets'),
        ('assets/golden_boulder.png', 'assets'),
        ('assets/grass.png', 'assets'),
        ('assets/hill_1.png', 'assets'),
        ('assets/hill_2.png', 'assets'),
        ('assets/level-up.mp3', 'assets'),
        ('assets/money-pickup.mp3', 'assets'),
        ('assets/jump.mp3', 'assets'),
        ('assets/music-icon.png', 'assets'),
        ('assets/next-icon.png', 'assets'),
        ('assets/splash.png', 'assets'),
        ('assets/Endless-Journey.mp3', 'assets'),
        ('assets/Endless-Ascent.mp3', 'assets'),
    ],
    hiddenimports=['pymunk.pygame_util'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove any pkg_resources related files from the bundle
a.binaries = [x for x in a.binaries if not x[0].startswith('pkg_resources')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Squaresyphus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico'  # Optional: Add this if you have an icon file
) 