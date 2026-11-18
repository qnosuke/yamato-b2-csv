#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ヤマト運輸 B2クラウド送り状取込CSV(基本レイアウト・95列)を標準出力へ出力する。

使い方(リポジトリのルートで実行):
  mkdir -p output
  python3 scripts/generate_csv.py --dest-name "東京" --dest-company "株式会社サンプル商事 営業部" \
    --zip 100-0001 --addr "東京都千代田区千代田1-1-1" --tel 03-0000-0000 \
    --date 2026/12/01 --time am --item "カタログ 30枚" > output/b2csv_20261201_090000.csv

- --time am は午前中(0812)。他: 1416/1618/1820/1921。省略時は指定なし。
- CSV本文は標準出力、進行メッセージは標準エラー出力へ出る。
- 先頭にUTF-8(BOM)、行末はCRLFで出力する(B2クラウド取込仕様に合わせている)。
- 差出人・請求先は config/sender.json から読む(sender.example.json をコピーして作る)。
- ファイルへの書き込みはシェルのリダイレクトで行う( > output/b2csv_YYYYMMDD_HHMMSS.csv )。
"""
import argparse
import csv
import datetime
import json
import os
import sys

CONFIG_PATH = os.path.join("config", "sender.json")
EXAMPLE_HINT = "cp config/sender.example.json config/sender.json"

TIME_MAP = {"am": "0812", "1416": "1416", "1618": "1618", "1820": "1820", "1921": "1921"}

REQUIRED_KEYS = [
    "sender_tel",
    "sender_zip",
    "sender_addr",
    "sender_name",
    "name_kana",
    "billing_customer_code",
]

OPTIONAL_DEFAULTS = {
    "sender_addr2": "",
    "billing_class": "",
    "freight_manage_no": "01",
}


def load_config():
    """config/sender.json を読み、必須キーをチェックする。"""
    if not os.path.exists(CONFIG_PATH):
        sys.exit(
            "設定ファイル config/sender.json がありません。\n"
            "リポジトリのルートで実行し、まず設定ファイルを用意してください:\n"
            "  " + EXAMPLE_HINT
        )
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    missing = [k for k in REQUIRED_KEYS if not cfg.get(k)]
    if missing:
        sys.exit("config/sender.json に必須キーがありません: " + ", ".join(missing))
    merged = dict(OPTIONAL_DEFAULTS)
    merged.update(cfg)
    return merged


def build_row(args, cfg):
    """B2基本レイアウト95列(No.1〜95)をこの順で組み立てる。"""
    todoke = TIME_MAP.get(args.time or "", "")
    today = datetime.date.today().strftime("%Y/%m/%d")
    row = [
        args.manage_no or "",          # 1 お客様管理番号
        "0",                           # 2 送り状種類 (0=発払い)
        "",                            # 3 クール区分
        "",                            # 4 伝票番号
        args.ship_date or today,       # 5 出荷予定日
        args.date or "",               # 6 お届け予定日
        todoke,                        # 7 配達時間帯
        "",                            # 8 お届け先コード
        args.tel,                      # 9 お届け先電話番号
        "",                            # 10 電話番号枝番
        args.zip,                      # 11 郵便番号
        args.addr,                     # 12 住所
        args.addr2 or "",              # 13 住所2(ビル名)
        args.dest_company or "",       # 14 会社・部門名1
        args.dest_company2 or "",      # 15 会社・部門名2
        args.dest_name,                # 16 お届け先名
        "",                            # 17 略称カナ
        "",                            # 18 敬称
        "",                            # 19 ご依頼主コード
        cfg["sender_tel"],             # 20 依頼主電話番号
        "",                            # 21 枝番
        cfg["sender_zip"],             # 22 依頼主郵便番号
        cfg["sender_addr"],            # 23 依頼主住所
        cfg["sender_addr2"],           # 24 依頼主住所2
        cfg["sender_name"],            # 25 依頼主名
        cfg["name_kana"],              # 26 依頼主略称カナ
        "",                            # 27 品名コード1
        args.item,                     # 28 品名1
        "",                            # 29 品名コード2
        "",                            # 30 品名2
        "",                            # 31 荷扱い1
        "",                            # 32 荷扱い2
        "",                            # 33 記事
        "",                            # 34 コレクト代金引換額
        "",                            # 35 コレクト内消費税額等
        "0",                           # 36 営業所止置き
        "",                            # 37 営業所コード
        "1",                           # 38 発行枚数
        "1",                           # 39 個数口枠の印字
        cfg["billing_customer_code"],  # 40 ご請求先顧客コード(ハイフン前の10桁)
        cfg["billing_class"],          # 41 ご請求先分類コード(ハイフン後が2桁なら空欄)
        cfg["freight_manage_no"],      # 42 運賃管理番号(公式FAQ a_id/576)
        "0",                           # 43 クロネコwebコレクトデータ登録
        "",                            # 44 加盟店番号
        "",                            # 45 受付番号1
        "",                            # 46 受付番号2
        "",                            # 47 受付番号3
        "0",                           # 48 お届け予定eメール利用区分
        "",                            # 49 e-mailアドレス
        "1",                           # 50 入力機種
        "",                            # 51 メッセージ
        "0",                           # 52 お届け完了eメール利用区分
        "",                            # 53 e-mailアドレス
        "",                            # 54 メッセージ
        "0",                           # 55 クロネコ収納代行利用区分
        "0",                           # 56 予備
        "",                            # 57 収納代行請求金額
        "",                            # 58 収納代行内消費税額等
        "",                            # 59 収納代行請求先郵便番号
        "",                            # 60 収納代行請求先住所
        "",                            # 61 収納代行請求先住所2
        "",                            # 62 収納代行請求先会社・部門名1
        "",                            # 63 収納代行請求先会社・部門名2
        "",                            # 64 収納代行請求先名(漢字)
        "",                            # 65 収納代行請求先名(カナ)
        "",                            # 66 収納代行問合せ先名
        "",                            # 67 収納代行問合せ先郵便番号
        "",                            # 68 収納代行問合せ先住所
        "",                            # 69 収納代行問合せ先住所2
        "",                            # 70 収納代行問合せ先電話番号
        "",                            # 71 収納代行管理番号
        "",                            # 72 収納代行品名
        "",                            # 73 収納代行備考
        "",                            # 74 複数口くくりキー
        "",                            # 75 検索キータイトル1
        "",                            # 76 検索キー1
        "",                            # 77 検索キータイトル2
        "",                            # 78 検索キー2
        "",                            # 79 検索キータイトル3
        "",                            # 80 検索キー3
        "",                            # 81 検索キータイトル4
        "",                            # 82 検索キー4
        "",                            # 83 検索キータイトル5
        "",                            # 84 検索キー5
        "",                            # 85 予備
        "",                            # 86 予備
        "",                            # 87 投函予定メール利用区分
        "",                            # 88 投函予定メールe-mail
        "",                            # 89 投函予定メールメッセージ
        "",                            # 90 投函完了メール(お届け先宛)利用区分
        "",                            # 91 投函完了メール(お届け先宛)e-mail
        "",                            # 92 投函完了メール(お届け先宛)メッセージ
        "",                            # 93 投函完了メール(ご依頼主宛)利用区分
        "",                            # 94 投函完了メール(ご依頼主宛)e-mail
        "",                            # 95 投函完了メール(ご依頼主宛)メッセージ
    ]
    return row


def main():
    p = argparse.ArgumentParser(description="B2クラウド基本レイアウト95列CSVを標準出力へ出力する")
    p.add_argument("--dest-name", required=True, help="お届け先名(姓のみ・敬称なし)")
    p.add_argument("--dest-company", default="", help="会社・部門名1(法人名のみ)")
    p.add_argument("--dest-company2", default="", help="会社・部門名2(部署・店舗名)")
    p.add_argument("--zip", required=True, help="お届け先郵便番号(ハイフン可)")
    p.add_argument("--addr", required=True, help="お届け先住所(都道府県から)")
    p.add_argument("--addr2", default="", help="お届け先建物名")
    p.add_argument("--tel", default="", help="お届け先TEL(ハイフン可。空欄でも取込可)")
    p.add_argument("--date", help="お届け予定日 YYYY/MM/DD")
    p.add_argument("--ship-date", help="出荷予定日 YYYY/MM/DD(省略時は今日)")
    p.add_argument("--time", help="配達時間帯: am/1416/1618/1820/1921")
    p.add_argument("--item", required=True, help="品名(枚数まで書く。例: カタログ 30枚)")
    p.add_argument("--manage-no", default="", help="お客様管理番号")
    args = p.parse_args()

    args.zip = args.zip.replace("-", "")
    args.tel = args.tel.replace("-", "")

    cfg = load_config()
    row = build_row(args, cfg)

    # B2クラウドはUTF-8(BOM付き)/Shift_JISのCSVを取込可能。ここではBOM付きUTF-8で出す
    sys.stdout.write("\ufeff")
    w = csv.writer(sys.stdout)
    # 1行目: B2のデフォルト取込開始行が2行目のための注記行(スキップされる)
    w.writerow(["ヘッダー行(B2取込開始行=2のためスキップされます)"])
    w.writerow(row)
    print("95列のCSVを出力しました。リダイレクト先は output/ 配下を推奨", file=sys.stderr)


if __name__ == "__main__":
    main()
