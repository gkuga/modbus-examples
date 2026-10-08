# データモデル (テーブル、レジスタ、レジスタマップ)

## 4 つのテーブル (Application 4.3 MODBUS Data model)

> MODBUS bases its data model on a series of tables that have distinguishing characteristics. The four primary tables are: ...

テーブルは **同じ種類のデータを番号順に並べた表**。プログラムで言えば 4 つの別々の配列。

| テーブル | 1 個の大きさ | アクセス | 規格の説明 | 典型的な用途 | FC (読み / 書き) |
| --- | --- | --- | --- | --- | --- |
| Discrete Inputs | 1 bit | 読み取り専用 | provided by an I/O system | スイッチ、センサーの接点 | 0x02 / なし |
| Coils | 1 bit | 読み書き | alterable by an application program | リレー、ランプ | 0x01 / 0x05, 0x0F |
| Input Registers | 16 bit | 読み取り専用 | provided by an I/O system | 温度、電圧などの計測値 | 0x04 / なし |
| Holding Registers | 16 bit | 読み書き | alterable by an application program | 設定値、目標値 | 0x03 / 0x06, 0x10 |

```
coils[0..65535]               1bit  読み書き
discrete_inputs[0..65535]     1bit  読むだけ
input_registers[0..65535]     16bit 読むだけ
holding_registers[0..65535]   16bit 読み書き
```

- **どのテーブルかは FC で決まる。** PDU にテーブルを指定する欄はない
- **テーブルの中の位置はアドレスで決まる。** テーブルごとに 0〜65535 が独立している
- 読み取り専用のテーブルには書き込み用の FC が存在しない。読み取り専用は「FC がない」ことで実現されている
- 全部の番号が実装されているわけではない。ないアドレスを読むと例外 0x02 (Illegal Data Address)
- 正確に「レジスタ」と呼ぶのは 16 bit の 2 種類。1 bit の 2 種類は「コイル」「ディスクリート」

### 2×2 の分類

もとは PLC の入出力をそのまま表している。

| | 1 bit (ON/OFF) | 16 bit (数値) |
| --- | --- | --- |
| 機器が決める (読むだけ) | Discrete Inputs | Input Registers |
| 外から変えられる (読み書き) | Coils (リレーのコイルが名前の由来) | Holding Registers |

ただし Application 4.3 はこう念を押している:

> The distinctions between inputs and outputs, and between bit-addressable and word-addressable data items, do not imply any application behavior.

分類の軸は物理的な入出力端子ではなく、**1 bit か 16 bit か** と **機器が決める値か、外から変えてよい値か**。
power-meter の Discrete Input 0 (電力超過アラーム) は物理入力ではなく機器内部の計算結果だが、
「機器が決めて外からは変えられない 1 bit」なので Discrete Inputs に置いている。

## レジスタはメモリのアドレスではない

Application 4.3:

> physical address in memory should not be confused with data reference. The only requirement is to link data reference with physical address.

機器内部のデータをどのレジスタ番号で見せるかは自由。

## レジスタマップ

**「どのアドレスに何のデータが入っているか」を示す、メーカーごとの対応表。**
規格は箱の番号を決めるだけで、中身の意味は一切決めない。

Application 4.4:

> The pre-mapping between the MODBUS data model and the device application is totally vendor device specific.

PDU に入っているのは 16 bit の値の並びだけで、「これは電圧」といった情報は含まれない。
マップを知らない第三者には `[18533, 27756, ...]` という数値の列にしか見えない。Modbus のデータは自己記述的ではない。

この点が BACnet との大きな違い。BACnet はオブジェクトモデルと探索 (Who-Is) を持ち、
規格に PICS (Protocol Implementation Conformance Statement)、業界に EDE ファイルという交換形式がある。
**Modbus には標準の設定ファイル形式がない。** レジスタマップは PDF や Excel で配られる。

例外的なもの:

- **SunSpec Modbus**: 太陽光インバータや蓄電池の業界でレジスタマップ自体を標準化したもの
- **Read Device Identification (0x2B / 0x0E)**: メーカー名・型番・バージョンだけは読み出せる ([04](04-function-codes.md))

### マップを読むときにつまずくところ

**1. 番号表記の 1 ずれ**

Application 4.4: データモデル上の番号は 1 から、PDU 上のアドレスは 0 から (「numbered X is addressed in the PDU X-1」)。

| 慣習的な番号 | テーブル | PDU 上のアドレス |
| --- | --- | --- |
| 00001〜 | Coils | 0〜 |
| 10001〜 | Discrete Inputs | 0〜 |
| 30001〜 | Input Registers | 0〜 |
| 40001〜 | Holding Registers | 0〜 |

先頭の桁がテーブルを表すのは、アドレスだけではどのテーブルか区別できないから。
マップが 0 始まりか 1 始まりかは最初に確認する。

**2. 倍率と単位**

レジスタには整数しか入らないので、小数は倍率を掛けて整数にする。電圧 `1015` が「0.1 V 単位」なら 101.5 V。

**3. 符号**

レジスタ自体に符号の情報はない。`65263` (0xfeef) は UINT16 なら 65263、INT16 (2 の補数) なら -273。
最上位ビットが 1 (0x8000 以上) なら負。どちらで読むかはマップで決まる。

**4. 16 bit を超えるデータとワードオーダー**

32 bit の整数や float はレジスタ 2 個にまたがる。**どちらのレジスタが上位か (ワードオーダー) は機器によって違い、規格は決めていない。**

```
123456 = 0x0001_e240
上位ワードが先: [0x0001, 0xe240]
下位ワードが先: [0xe240, 0x0001]   ← 逆に解釈すると 0xe240_0001 = 3795845121
```

pymodbus の `convert_from_registers(..., word_order="big" / "little")` はこの違いに合わせるための引数。
INT32, FLOAT32 などの型も規格にはなく、ほぼ全ての機器が使うので pymodbus が便宜的に用意しているもの。

### 実務でよくあるマップの形

- **全部 Holding Registers に置く**: 計測値のような読み取り専用データまで 4xxxx に置き、書き込まれたら例外を返す。
  FC 0x03 しか使えないマスタに合わせるため。かなり多い
- **ビットをレジスタに詰める (ステータスワード)**: 状態や警報を Coils / Discrete Inputs に置かず、1 レジスタの各ビットに意味を割り当てる。
  1 回で 16 個取れるが、ビットの意味はマップを見ないと分からない
- **Coils をコマンドに使う**: ON を書くと 1 回実行され自動で OFF に戻る (リセット、運転開始など)

自分で設計するなら 2×2 の分類に従うのが素直。他社の機器を読むときは、使い分けている前提を置かず **マップに書かれたテーブルと FC に従う**。

## テーブルの重ね合わせ

Application 4.3 は、4 つのテーブルが **同じデータを指していてもよい** と明記している。

> It is perfectly acceptable, and very common, to regard all four tables as overlaying one another, if this is the most natural interpretation on the target machine in question.

- Example 1 "Device having 4 separate blocks": 4 つが別々 (power-meter)
- Example 2 "Device having only 1 block": 1 つの領域を 16 bit 単位でもビット単位でも読める (hello-tcp)

テーブルは「データの置き場所」というより **データへのアクセス方法の分類** と考えるほうが正確。

### Coil に 16 bit を置けるわけではない

Coil は通信上いつも 1 bit。各テーブルの単位は規格が決めている。
重ね合わせとは「同じメモリを、16 bit 単位でも 1 bit 単位でも見せる」こと。

hello-tcp サーバ (1 ブロック共有) で同じ領域を 2 通りに読んだ結果:

```
FC 03 アドレス 0 を 1 個
  TX: 03 00 00 00 01
  RX: 03 02 48 65              → 0x4865 = "He"

FC 01 アドレス 0 から 16 個
  TX: 01 00 00 00 10
  RX: 01 02 65 48              → 同じ 16 bit がコイル 16 個として返る
```

### バイト列は違うが、データは同じ

FC 03 では `48 65`、FC 01 では `65 48`。FC ごとに詰め方の規則が違うため:

| | 規則 | 規格 |
| --- | --- | --- |
| レジスタ | 16 bit の値を上位バイト → 下位バイトの順で送る | Application 4.2 (ビッグエンディアン) |
| コイル | 8 個ずつ 1 byte に詰め、若い番号を最下位ビットに置く | Application 6.1 |

正しくほどくと同じ値に戻る:

```
コイル 0〜7  : 0x65 → 1,0,1,0,0,1,1,0
コイル 8〜15 : 0x48 → 0,0,0,1,0,0,1,0
コイル n を bit n として組み直す → 0100 1000 0110 0101 = 0x4865
```

ただし **どのビットとどのコイル番号を対応させるかは規格で決まっていない。**
pymodbus は「コイル n = レジスタの bit n (最下位から)」だが、最上位ビットから対応させる機器もあり得る。

- 指しているデータは同じ
- バイト列は FC ごとの規則で変わる
- ほどき方 (ビットとコイルの対応) は機器の仕様で確認が必要

実務で重ね合わせている機器はそれほど多くなく、主に PLC (内部メモリをワードでもビットでも見せる設計)。
マップに「40001 の bit 3 = Coil 00004 と同じ」のような記載があれば重ねている機器。
