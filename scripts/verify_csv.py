#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B2クラウド取込CSV(95列)の検証ツール。

使い方(リポジトリのルートで実行):
  python3 scripts/verify_csv.py output/b2csv_xxx.csv --diff templates/b2_basic_layout_95.csv

チェック内容:
  - UTF-8(BOM付き)・CRLF行末
  - 1行目が注記行(1列)、全データ行が95列
  - 列5 出荷日 / 列6 着日が YYYY/MM/DD(半角)
  - 列9 TEL・列11 郵便番号にハイフンが混入していないこと
  - 列16 宛名・列28 品名が空でないこと
  - --diff 指定時: テンプレとの差分列が許可リスト(--allowed)内のみか判定
終了コード: 問題なければ 0、異常があれば 1。エージェントの自己検証に使う。
"""
import argparse
import csv
import re
import sys

NOTE_MARK = "ヘッダー行"
COLS = 95
DEFAULT_ALLOWED = "5,6,7,9,11,12,13,14,15,16,28"
DATE_RE = re.compile(r"^\d{4}/\d{2}/\d{2}$")


def fail(msgs, msg):
    msgs.append("NG: " + msg)


def main():
    p = argparse.ArgumentParser(description="B2取込CSV(95列)を検証する")
    p.add_argument("csv", help="検証するCSVファイル")
    p.add_argument("--diff", help="差分比較元のテンプレCSV(2行目を比較)")
    p.add_argument("--allowed", default=DEFAULT_ALLOWED,
                   help="diffで差し替えを許容する列(1始まりカンマ区切り)")
    args = p.parse_args()

    msgs = []

    raw = open(args.csv, "rb").read()
    if not raw.startswith(b"\xef\xbb\xbf"):
        fail(msgs, "UTF-8のBOMがありません(先頭3バイトがEF BB BFでない)")
    body = raw.replace(b"\r\n", b"")
    if b"\n" in body:
        fail(msgs, "CRLF以外の改行(LFのみの行)が混ざっています")
    if b"\r\n" not in raw:
        fail(msgs, "CRLF行末ではありません")

    with open(args.csv, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))

    if not rows:
        sys.exit("NG: CSVが空です")
    if len(rows[0]) != 1 or NOTE_MARK not in rows[0][0]:
        fail(msgs, "1行目が注記行ではありません(「%s」を含む1列の行であること)" % NOTE_MARK)

    data_rows = rows[1:]
    if not data_rows:
        fail(msgs, "データ行(2行目以降)がありません")
    for i, r in enumerate(data_rows, start=2):
        if len(r) != COLS:
            fail(msgs, "%d行目の列数が95ではありません(%d列)" % (i, len(r)))

    def col(row, n):
        return row[n - 1] if len(row) >= n else ""

    for i, r in enumerate(data_rows, start=2):
        c5, c6 = col(r, 5), col(r, 6)
        if not DATE_RE.match(c5):
            fail(msgs, "%d行目 列5 出荷日がYYYY/MM/DDではありません: %r" % (i, c5))
        if c6 and not DATE_RE.match(c6):
            fail(msgs, "%d行目 列6 着日がYYYY/MM/DDではありません: %r" % (i, c6))
        c9 = col(r, 9)
        if c9 and not c9.isdigit():
            fail(msgs, "%d行目 列9 TELにハイフン等が混ざっています: %r(ハイフンなし半角で書く)" % (i, c9))
        c11 = col(r, 11)
        if c11 and not (c11.isdigit() and len(c11) == 7):
            fail(msgs, "%d行目 列11 郵便番号がハイフンなし7桁ではありません: %r" % (i, c11))
        if not col(r, 16):
            fail(msgs, "%d行目 列16 宛名が空です" % i)
        if not col(r, 28):
            fail(msgs, "%d行目 列28 品名が空です" % i)

    if args.diff:
        allowed = {int(x) for x in args.allowed.split(",") if x.strip()}
        with open(args.diff, encoding="utf-8-sig", newline="") as f:
            tpl_rows = list(csv.reader(f))
        if len(tpl_rows) < 2:
            sys.exit("NG: テンプレCSVにデータ行がありません")
        tpl = tpl_rows[1]
        for i, r in enumerate(data_rows, start=2):
            diffs = []
            for n in range(1, min(len(tpl), COLS) + 1):
                if col(r, n) != col(tpl, n):
                    diffs.append(n)
            bad = [n for n in diffs if n not in allowed]
            print("%d行目の差分列: %s" % (i, diffs or "なし"))
            for n in diffs:
                if n not in allowed:
                    fail(msgs, "%d行目 列%d は差し替え許可外の列です: %r (テンプレ: %r)"
                         % (i, n, col(r, n), col(tpl, n)))
        print("許可列: %s" % sorted(allowed))

    for m in msgs:
        print(m)
    if msgs:
        print("結果: NG(%d件)" % len(msgs))
        sys.exit(1)
    print("結果: OK")


if __name__ == "__main__":
    main()
