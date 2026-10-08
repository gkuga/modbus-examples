# 規格と階層構造

## 規格の構成

Modbus の規格は 1 つではなく、「何を送るか」と「どう運ぶか」で文書が分かれている。

| 文書 | 定義している範囲 |
| --- | --- |
| Application Protocol Specification | PDU (ファンクションコード + データ) の意味。運び方には依存しない |
| over Serial Line | シリアル線での運び方。スレーブアドレス、CRC/LRC、RTU/ASCII、RS-485 の電気仕様 |
| Messaging on TCP/IP Implementation Guide | TCP での運び方。MBAP ヘッダ、ポート 502、ゲートウェイの振る舞い |

この他に Modbus/TCP Security (TLS) もある。
Modbus は国際規格 IEC 61158 / IEC 61784 にも含まれているが、実務で参照するのは modbus.org の文書。

pymodbus はこれらを実装したライブラリで、TCP / RTU / ASCII / TLS / UDP のクライアントとサーバを作れる。

## OSI 参照モデルとの対応

Application の冒頭で、Modbus は **OSI 参照モデル第 7 層 (アプリケーション層) のメッセージングプロトコル** と定義されている。

```
                 Modbus TCP                      Modbus RTU
             ┌───────────────────────────────────────────────────────┐
 7 アプリ    │   Application Protocol (PDU: ファンクションコード + データ)   │
             ├──────────────────────────┬────────────────────────────┤
             │ MBAP ヘッダ              │                            │
 4 トランスポート │ TCP (ポート 502)      │   (3〜6 層はない)           │
 3 ネットワーク  │ IP                    │                            │
             ├──────────────────────────┼────────────────────────────┤
 2 データリンク  │ Ethernet              │ Serial Line Protocol       │
             │                          │ (スレーブアドレス + CRC)      │
 1 物理      │ Ethernet                 │ RS-485 / RS-232            │
             └──────────────────────────┴────────────────────────────┘
```

シリアルの Modbus には第 3〜6 層がない。経路制御も分割もない 1 本の線上のやりとりなので、第 2 層の上に直接第 7 層が乗る。

## PDU と ADU

- **PDU (Protocol Data Unit)**: 運び方に依存しない中身。ファンクションコード (1 byte) + データ
- **ADU (Application Data Unit)**: PDU に運び方ごとの包装を付けたもの

```
RTU の ADU: [スレーブアドレス 01] [PDU 03 00 00 00 07] [CRC 04 08]
TCP の ADU: [MBAP 00 01 00 00 00 06 01] [PDU 03 00 00 00 07]
```

hello-tcp と hello-rtu で同じリクエスト (保持レジスタ 0 から 7 個読む) を送ると、真ん中の PDU は完全に同じになる。
第 7 層が共通で、下の層だけが差し替わっているから。ゲートウェイが TCP と RTU を変換できるのもこの構造のおかげ
(外側の包装だけ付け替えれば済む)。

pymodbus ではこの包装を担当する部分を framer と呼ぶ (`FramerType.SOCKET` / `FramerType.RTU` / `FramerType.ASCII`)。

## MBAP ヘッダ (TCP 3.1.3)

```
00 01 | 00 00 | 00 06 | 01 | 03 00 00 00 07
 |       |       |      |    └ PDU
 |       |       |      └ Unit Identifier (1 byte)
 |       |       └ Length: 後続バイト数 = Unit Identifier + PDU (2 byte)
 |       └ Protocol Identifier: Modbus は常に 0 (2 byte)
 └ Transaction Identifier: リクエストとレスポンスの対応付け (2 byte)
```

TCP 自体に誤り検出があるので、RTU のような CRC は付かない。

## RTU と ASCII (Serial 2.5)

RTU は **Remote Terminal Unit (遠隔端末装置)** の略。もとは SCADA の用語で、現場に置かれて中央と通信する装置のこと。
Modbus では装置ではなく **シリアル伝送モードの名前** として使われる。

| モード | データの送り方 | 例 (`03 00 00 00 07` を送る) | 誤り検出 | フレームの区切り |
| --- | --- | --- | --- | --- |
| RTU | バイナリのまま | `01 03 00 00 00 07 04 08` (8 byte) | CRC-16 | 3.5 文字分の無通信時間 |
| ASCII | 1 byte を 16 進 2 文字にして `:` 〜 CRLF で囲む | `:010300000007F5\r\n` (17 文字) | LRC | 開始文字と終端文字 |

RTU は同じ内容を約半分のサイズで送れるので主流。ASCII は人が読めるが、今はあまり使われない。

## TCP と RTU の違いのまとめ

| | TCP | RTU |
| --- | --- | --- |
| ヘッダ | MBAP (7 byte) | スレーブアドレス (1 byte) |
| 誤り検出 | なし (TCP に任せる) | CRC-16 |
| フレームの区切り | Length フィールド | 無通信時間 |
| 同時リクエスト | 複数可 (Transaction Identifier で区別) | 1 往復ずつ |
| PDU | 共通 | 共通 |
