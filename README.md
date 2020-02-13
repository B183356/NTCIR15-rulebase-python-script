# NTCIR15 賛否予測ルールベーススクリプト

## タスク概要

[都議会だより](https://www.gikai.metro.tokyo.jp/newsletter/)にある会議録のうち、議員の発言などを利用してその議員の属する会派の議題に対しての賛否を予測する。

## データセット

リンク準備中

*****

## プログラム概要

前述のタスクに対して、ルールベースで取り組んだスクリプト。
定例会の議事録のみ使用。
各会期の終盤には、各会派から代表者が自分の立場を明らかにして討論を行う部分があるので、そこから意見を引っ張って来た。
ただし、討論を行わない(党勢的な理由で行う時間を与えられない?)会派もあるので、そこから抽出することはできない。

## 内容

- NTCIR15-rulebase.py
実行用スクリプト

- NTCIR15Util.py
使う(予定だった)関数など

- README.md
説明書MDファイル

## 実行

### 必要ライブラリ

プログラムを実行するには、漢字と数字の変換を行うライブラリの[kanjize](https://github.com/delta114514/Kanjize)が必要になります。

###### インストール

```pip3 install kanjize```

自分の実行環境に合わせて適切にインストールしてください。

### 実行
PATHは適宜読み替えてください。

- 単一ファイルを対象とする場合

```python NTCIR15-rulebase.py 出題jsonファイル 本会議/定例会/議事録jsonファイル```

- 複数ファイルを対象とする場合

```python NTCIR-rulebase.py -d 出題jsonファイルの入っているディレクトリ 本会議/定例会/議事録jsonファイル```

### 出力

フラグを弄ってなければこのように出力が出ます。





