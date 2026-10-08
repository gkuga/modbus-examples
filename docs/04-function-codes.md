# ファンクションコード (FC)

## 基本

**FC は PDU の最初の 1 byte。** フレーム全体 (ADU) の先頭ではない。

```
RTU: [01] [03 00 00 00 07] [CRC]       TCP: [00 01 00 00 00 06 01] [03 00 00 00 07]
          ↑ PDU の先頭 = FC                                         ↑ PDU の先頭 = FC
```

Application 4.1:

- 1〜127 が正常なリクエスト / レスポンス用。**0 は無効**
- 128〜255 は **例外レスポンス専用** (元の FC + 0x80)
- 正常なレスポンスはリクエストと同じ FC をそのまま返す

## 分類

規格には 2 種類の分け方がある。

### 誰が定義したか (Application 5)

| 分類 | 範囲 | 内容 |
| --- | --- | --- |
| Public | 下の 2 つ以外 | 規格が定義。一意で、適合試験もある |
| User-Defined | 65〜72、100〜110 | メーカーが独自機能に自由に使える (一意性の保証はない) |
| Reserved | 9, 10, 13, 14, 41, 42, 90, 91, 125〜127 など | 昔の製品が使っていて新規には使えない (Annex A) |

### 何をするか (Application 5.1 Public Function Code Definition)

**Data Access**

| 小分類 | 対象 | FC |
| --- | --- | --- |
| Bit access | Physical Discrete Inputs | 0x02 Read Discrete Inputs |
| | Internal Bits または Physical Coils | 0x01 Read Coils, 0x05 Write Single Coil, 0x0F Write Multiple Coils |
| 16 bits access | Physical Input Registers | 0x04 Read Input Registers |
| | Internal Registers または Physical Output Registers | 0x03 Read Holding Registers, 0x06 Write Single Register, 0x10 Write Multiple Registers, 0x17 Read/Write Multiple Registers, 0x16 Mask Write Register, 0x18 Read FIFO Queue |
| File record access | (ファイル) | 0x14 Read File Record, 0x15 Write File Record |

**Diagnostics** (0x2B 以外は Serial Line only)

| FC | 名前 |
| --- | --- |
| 0x07 | Read Exception Status |
| 0x08 | Diagnostics (サブファンクションで機能を選ぶ) |
| 0x0B | Get Comm Event Counter |
| 0x0C | Get Comm Event Log |
| 0x11 | Report Server ID |
| 0x2B / 0x0E | Read Device Identification |

**Other**

| FC | 名前 |
| --- | --- |
| 0x2B / 0x0D, 0x0E | Encapsulated Interface Transport |
| 0x2B / 0x0D | CANopen General Reference |

### 実務の感覚

- よく使うのは 0x01〜0x06, 0x0F, 0x10 の 8 個
- 安い機器は 0x03, 0x04, 0x06 しか対応していないことも珍しくない
- 対応していない FC を送ると例外 0x01 (Illegal Function)
- どの FC に対応しているかもレジスタマップと同じく機器のマニュアルに書かれている

## よく使う FC の PDU

power-meter で実際にやりとりした PDU (MBAP ヘッダを除く)。

### 読み出し (0x01〜0x04) のリクエストは全部同じ形

```
04 | 00 00 | 00 08
FC   開始アドレス  個数
```

### 0x03 / 0x04 のレスポンス: レジスタの値が 2 byte ずつ並ぶ

```
04 | 10 | 03 f3 | 01 99 | 01 94 | 03 d1 | 42 48 20 aa | e2 41 00 01
FC   バイト数  [0]     [1]     [2]     [3]     [4][5]        [6][7]
     (16)
```

### 0x01 / 0x02 のレスポンス: ビットが 1 byte に詰められる

```
01 | 01 | 01
FC   バイト数  ビット列 0b00000001 → 最下位ビット = Coil 0 = ON
```

### 0x05 / 0x06: 1 個書く。正常時のレスポンスはリクエストのエコー

```
06 | 00 00 | 00 00        05 | 00 00 | ff 00
FC   アドレス  値            FC   アドレス  ON
```

**コイルの ON は `ff 00`、OFF は `00 00`** と規格で決まっている。`00 01` は ON ではない。

### 0x10: 複数のレジスタにまとめて書く

```
リクエスト: 10 | 00 00 | 00 02 | 04 | 03 e8 00 00
            FC   開始     個数   バイト数  値 [1000, 0]
レスポンス: 10 | 00 00 | 00 02            ← 値は返さず開始アドレスと個数だけ
```

## 例外レスポンス

```
86 | 04
FC 0x06 + 0x80   例外コード
```

FC の最上位ビットが立っていれば例外。続く 1 byte が理由。

| 例外コード | 名前 | 意味 |
| --- | --- | --- |
| 0x01 | Illegal Function | 対応していない FC |
| 0x02 | Illegal Data Address | 存在しないアドレス |
| 0x03 | Illegal Data Value | 値が不正 |
| 0x04 | Server Device Failure | 機器の内部エラー |
| 0x05 | Acknowledge | 受け付けたが処理に時間がかかる (プログラミング用途) |
| 0x06 | Server Device Busy | 処理中 (プログラミング用途) |
| 0x08 | Memory Parity Error | ファイルレコードのパリティエラー |
| 0x0A | Gateway Path Unavailable | ゲートウェイが転送先を持たない |
| 0x0B | Gateway Target Device Failed to Respond | 転送したが相手が応答しない |

Application 7 の表にあるのはこの 9 個。0x07 (Negative Acknowledge) は FC 0x08 の NAK Count で言及されるが、現行の表には載っていない古いコード。

## 0x2B Encapsulated Interface Transport

**0x2B は Device Identification 専用の FC ではない。** Modbus の PDU の中に別のインターフェースを包んで運ぶ入れ物 (Application 6.19)。
次の 1 byte **MEI Type** (MODBUS Encapsulated Interface Type) で中身を選ぶ。

| MEI Type | 中身 | 規格 |
| --- | --- | --- |
| 0x0D | CANopen General Reference | 6.20 |
| 0x0E | Read Device Identification | 6.21 |
| 0x00〜0x0C, 0x0F〜0xFF | 予約 | Annex A |

実質的な使い道が Device Identification しかなく、資料も「0x2B / 0x0E」とセットで書くので専用の FC だと思われがち。

FC の後ろで機能を枝分かれさせるのは 0x08 (サブファンクション 2 byte) も同じ。FC は 1 byte で 127 個しかないので、FC を消費せずに機能を増やす工夫。

## Read Device Identification (0x2B / 0x0E, Application 6.21)

```
2b | 0e | 01 | 00
FC   MEI  Read Device ID code  Object Id
```

**Read Device ID code が「どう読むか」、Object Id が「どこから・どれを読むか」。**

### Object Id

機器情報は「オブジェクト」の集まりとしてモデル化されている。レジスタと違い、**番号ごとの意味を規格が決めている**。値は ASCII 文字列。

| Object Id | 名前 | 必須 | カテゴリ |
| --- | --- | --- | --- |
| 0x00 | VendorName | **必須** | Basic |
| 0x01 | ProductCode | **必須** | Basic |
| 0x02 | MajorMinorRevision | **必須** | Basic |
| 0x03 | VendorUrl | 任意 | Regular |
| 0x04 | ProductName | 任意 | Regular |
| 0x05 | ModelName | 任意 | Regular |
| 0x06 | UserApplicationName | 任意 | Regular |
| 0x07〜0x7F | 予約 | | |
| 0x80〜0xFF | メーカー独自 (Private) | 任意 | Extended |

### Read Device ID code

| code | 読み方 | 返るもの |
| --- | --- | --- |
| 01 | Basic をまとめて (ストリームアクセス) | 0x00〜0x02 |
| 02 | Regular までまとめて | 0x00〜0x06 のうち実装されているもの |
| 03 | Extended までまとめて | 0x00〜0xFF のうち実装されているもの |
| 04 | 1 個だけ (個別アクセス) | Object Id で指定した 1 個 |

### レスポンス

| フィールド | 内容 |
| --- | --- |
| FC, MEI Type, Read Device ID code | リクエストと同じ |
| Conformity level | 機器の対応レベル。0x01/0x02/0x03 = Basic/Regular/Extended (ストリームのみ)、0x81/0x82/0x83 = 個別アクセスも可 |
| More Follows | 00 = これで全部、FF = 続きがある |
| Next Object Id | 続きがあるとき、次に要求するオブジェクト番号 |
| Number of objects | 返したオブジェクトの数 |
| オブジェクトの並び | ID (1 byte), 長さ (1 byte), 値 |

### 2 つの読み方

**ストリームアクセス (code 01〜03): Object Id は「どこから」**

```
TX: 2b 0e 02 00
RX: 2b 0e 02 83 00 00 05 | 00 05 "gkuga" | 01 04 "HM-1" | 02 03 "1.0" | 03 13 "https://example.com" | 04 0b "Hello Meter"
```

1 回に入りきらない (PDU は最大 253 byte) と More Follows = FF と Next Object Id が返るので、
Object Id にその値を入れて再度リクエストする。

**個別アクセス (code 04): Object Id は「どれを」**

```
TX: 2b 0e 04 04       → RX: 2b 0e 04 83 00 00 01 | 04 0b "Hello Meter"
TX: 2b 0e 04 10       → RX: ab 02 (存在しないので例外 02)
```

### 規格で決まっている細かい挙動

- ストリームアクセスで存在しない Object Id → オブジェクト 0 から返す
- 個別アクセスで存在しない Object Id → 例外 02 (Illegal Data Address)
- 不正な Read Device ID code → 例外 03 (Illegal Data Value)
- 対応レベルより上を要求された → エラーにせず、対応しているレベルまでを返す
- どのレベルでも Basic の 3 つは必須

### 実験結果

hello-tcp サーバ (`identity` 未設定) に問い合わせると:

```
TX: 2b 0e 01 00
RX: 2b 0e 01 83 00 00 00     ← Conformity 0x83 なのにオブジェクト 0 個
```

Basic は必須なので **規格違反の応答**。pymodbus は `SimDevice` に `identity` を設定しないとこうなる。

Device Identification は Modbus で数少ない自己記述的な情報。メーカーと型番が分かればどのレジスタマップを見ればよいか判断できるが、
レジスタの意味までは分からない。実機では未対応のことも多く、その場合は `ab 01` (Illegal Function)。
