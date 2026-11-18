#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B2クラウド取込画面の自動操作スクリプト(画像マッチ+クリック / macOS専用)。

使い方(リポジトリのルートで実行):
  python3 scripts/auto_import_gui.py dry <csvpath>   # クリックせずボタン検出のみ確認
  python3 scripts/auto_import_gui.py run <csvpath>   # 実行(取込結果表示まで。登録・印刷は押さない)

- B2クラウド「外部データから発行」画面を開いた状態で実行する。
- 起動するブラウザは環境変数 B2_BROWSER で指定できる(既定: Safari)。
- ボタン判定には reference/btn_fileselect.jpg と reference/btn_start.jpg を使う。
  解像度・拡大率が異なる環境では、自分の画面からボタン部分を切り出して差し替えること。
- 設計: 「取込み結果表示」で必ず停止する。登録完了・印刷は絶対に押さない。
"""
import os
import subprocess
import sys
import tempfile
import time

BROWSER = os.environ.get("B2_BROWSER", "Safari")
REF = "reference"
BTN_FILESELECT = os.path.join(REF, "btn_fileselect.jpg")
BTN_START = os.path.join(REF, "btn_start.jpg")


def screenshot():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    subprocess.run(["screencapture", "-x", path], check=True)
    from PIL import Image
    img = Image.open(path).convert("RGB")
    return img, path


def find_template(screen_img, tmpl_path, threshold=0.80):
    """画面内からテンプレート画像を探し、中心座標(画面座標系)を返す"""
    import numpy as np
    screen = np.asarray(screen_img, dtype=np.float32)
    from PIL import Image
    tmpl = np.asarray(Image.open(tmpl_path).convert("RGB"), dtype=np.float32)
    sh, sw = screen.shape[:2]
    th, tw = tmpl.shape[:2]
    if th > sh or tw > sw:
        return None, 0.0
    best, best_loc = -1.0, None
    # 粗探索: 2pxステップのスライディングウィンドウ
    t_norm = tmpl / 255.0
    step = 2
    for y in range(0, sh - th, step):
        for x in range(0, sw - tw, step):
            win = screen[y:y+th, x:x+tw] / 255.0
            d = np.mean((win - t_norm) ** 2)
            score = 1.0 - d
            if score > best:
                best, best_loc = score, (x, y)
    if best < threshold:
        return None, best
    cx, cy = best_loc[0] + tw // 2, best_loc[1] + th // 2
    return (cx, cy), best


def click(x, y):
    import Quartz
    for t, ty in [(Quartz.kCGEventLeftMouseDown, Quartz.kCGMouseButtonLeft),
                  (Quartz.kCGEventLeftMouseUp, Quartz.kCGMouseButtonLeft)]:
        ev = Quartz.CGEventCreateMouseEvent(None, t, (x, y), ty)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        time.sleep(0.05)


def keystroke_key(key, cmd=False, shift=False):
    import Quartz
    flags = 0
    if cmd: flags |= Quartz.kCGEventFlagMaskCommand
    if shift: flags |= Quartz.kCGEventFlagMaskShift
    keycode = {"g": 5, "return": 36}[key]
    if flags:
        ev = Quartz.CGEventCreateKeyboardEvent(None, keycode, True)
        Quartz.CGEventSetFlags(ev, flags)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        ev2 = Quartz.CGEventCreateKeyboardEvent(None, keycode, False)
        Quartz.CGEventSetFlags(ev2, flags)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev2)
    else:
        for down in (True, False):
            ev = Quartz.CGEventCreateKeyboardEvent(None, keycode, down)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
            time.sleep(0.03)


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("dry", "run"):
        sys.exit("使い方: python3 scripts/auto_import_gui.py dry|run <csvpath>")
    mode, csvpath = sys.argv[1], os.path.abspath(sys.argv[2])
    if not os.path.exists(csvpath):
        print(f"CSV not found: {csvpath}"); sys.exit(1)

    # 1. ブラウザをアクティブ化(B2の「外部データから発行」画面を開いておく)
    subprocess.run(["open", "-a", BROWSER], check=True)
    time.sleep(1)

    img, shot = screenshot()
    (fx, fs) = find_template(img, BTN_FILESELECT)
    print(f"ファイル選択ボタン: {'検出' if fx else '未検出'} score={fs:.3f} pos={fx}")

    if fx is None:
        print("DRY失敗: 取込画面が開いているか確認してください"); sys.exit(2)
    if mode == "dry":
        print("DRY OK: ファイル選択ボタンを検出。run モードで続行可能"); sys.exit(0)

    # 2. ファイル選択 → Finderダイアログ → Cmd+Shift+G → パス入力
    click(*fx); time.sleep(1.5)
    keystroke_key("g", cmd=True, shift=True); time.sleep(1)
    subprocess.run(["osascript", "-e",
        f'set the clipboard to "{csvpath}"'], check=True)
    keystroke_key("v", cmd=True); time.sleep(0.5)
    keystroke_key("return"); time.sleep(1)
    keystroke_key("return"); time.sleep(2.5)  # Open → 読込待ち

    # 3. 取込み開始
    img2, _ = screenshot()
    (sx, ss) = find_template(img2, BTN_START)
    print(f"取込み開始ボタン: {'検出' if sx else '未検出'} score={ss:.3f} pos={sx}")
    if sx is None:
        print("中止: 取込み開始ボタンが見つかりません(画面を確認してください)"); sys.exit(3)
    click(*sx); time.sleep(4)

    # 4. 結果表示で停止(登録・印刷は押さない)
    print("STOP: 取込を実行しました。以降の「登録完了・印刷」は手動で確認してください")


if __name__ == "__main__":
    main()
