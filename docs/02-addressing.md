# アドレス (Slave Address と Unit Identifier)

## どこで定義されているか

**Application (PDU) にはアドレスがない。** アドレスはそれぞれの運び方の規格が別々に定義している。

| 名前 | 規格 | 場所 | 層 |
| --- | --- | --- | --- |
| Slave Address | Serial 2.1, 2.2, 2.3 | RTU / ASCII フレームの先頭 1 byte | データリンク層 (第 2 層) |
| Unit Identifier | TCP 3.1.2, 3.1.3, 4.4.1.2 | MBAP ヘッダの 7 byte 目 | (TCP 上の Modbus 用ヘッダ) |

### Slave Address (Serial)

Serial 2.2 MODBUS Addressing rules:

| 0 | 1〜247 | 248〜255 |
| --- | --- | --- |
| Broadcast address | Slave individual addresses | Reserved |

- 1 本の RS-485 線を共有するので、どの機器宛てかを区別するために必須 (Ethernet の MAC アドレスに近い位置づけ)
- アドレスはバス上で一意でなければならない。マスタ自身はアドレスを持たない
- スレーブは応答に自分のアドレスを入れて返すので、マスタはどこからの応答か分かる
- 0 はブロードキャスト。全スレーブが実行するが誰も応答しない。書き込みコマンドだけに使える

### Unit Identifier (TCP)

TCP 3.1.2:

> The MODBUS 'slave address' field usually used on MODBUS Serial Line is replaced by a single byte 'Unit Identifier' within the MBAP Header.

- 本来の用途は、**1 つの IP アドレスの裏に複数の Modbus 機器がいる** 場合 (ゲートウェイ、ブリッジ) の宛先指定
- サーバは受け取った値をそのままレスポンスに入れて返す

## 名前の整理

- 規格上の正式名称は **Slave Address** (シリアル) と **Unit Identifier** (TCP)
- 「Slave ID」「Unit ID」「Device ID」は通称。pymodbus は両方まとめて `device_id` と呼ぶ (3.10 より前は `slave`)
- 最近は Master/Slave を Client/Server と言い換える流れがある (TCP の規格は最初から Client/Server)
- **Read Device Identification (FC 0x2B / 0x0E) はアドレスとは無関係** の別機能 ([04](04-function-codes.md) 参照)

## 値の範囲は規格ごとに違う

フィールドはどちらも 1 byte (0〜255) だが、有効な値と意味が違う。

| 値 | Serial (Slave Address) | TCP 直結の機器 | TCP ゲートウェイ経由 |
| --- | --- | --- | --- |
| 0 | ブロードキャスト | 受け付けてよい (TCP 4.4.1.2 Remark) | シリアル側でブロードキャストになる |
| 1〜247 | 個々のスレーブ | 規格上は意味なし | 先にあるそのスレーブ |
| 248〜255 | 予約 (使えない) | **0xFF を推奨** | 0xFF は「ゲートウェイの先ではない」 |

特に 0 と 0xFF はシリアルと TCP で意味が逆転している。共通のフィールドと考えると混乱する。

## ゲートウェイでの変換

TCP 4.4.1.2:

> the "Unit Identifier" carries the MODBUS slave address of the remote device

```
[TCP クライアント] --TCP--> [ゲートウェイ 192.168.0.10] --RS-485--> [スレーブ 1] [スレーブ 2] [スレーブ 3]

TCP:  00 01 00 00 00 06 | 02 | 03 00 00 00 07
                          ↑ Unit Identifier = 2
                ↓ ゲートウェイが MBAP を外し、CRC を付ける
RTU:  02 | 03 00 00 00 07 | CRC
      ↑ Slave Address = 2
```

- 規格上の基本形は「Unit Identifier の値 = Slave Address」をそのままコピー
- 実際のゲートウェイには対応表を設定できるものや、複数の RS-485 ポートを Unit ID の範囲で振り分けるもの (1〜99 はポート 1 など) もある。**変換の仕方はゲートウェイの仕様次第**
- ゲートウェイの転送先は **自分の RS-485 端子につながっている機器だけ**。Ethernet 側の他の TCP 機器には転送しない

## IP アドレスとの関係

TCP では、相手は **IP アドレス (+ ポート) と Unit Identifier の組** で決まる。

```
直結:          (192.168.0.20:502, 0xFF)  → IP だけで機器が決まり、Unit ID は使わない
ゲートウェイ:  (192.168.0.10:502, 1)     → IP でゲートウェイ、Unit ID でその先のスレーブ
               (192.168.0.10:502, 2)
               (192.168.0.11:502, 1)     → 別のゲートウェイの先の、別のスレーブ 1
```

- Unit ID は IP ごとに独立している。番号の一意性が必要なのは 1 本のシリアルバスの中だけ
- **Unit ID はネットワーク全体で通じるアドレスではない。** 届いた先の 1 台が中身を見て解釈するだけの値
- 「Unit ID 0xFF を持つ TCP 機器」という概念はない

### TCP で Unit ID に意味があるか

| 受け取る機器 | Unit ID の意味 |
| --- | --- |
| 直結の TCP 機器 (1 台で完結) | なし。規格は "useless" と書き、0xFF を推奨 |
| TCP→RTU ゲートウェイ | 必須。どのスレーブかを選ぶ (規格が想定する本来の用途) |
| 内部に複数ユニットを持つ TCP 機器 | 機器内のユニットを選ぶ (規格外だがメーカー独自によくある。集約装置など) |

実機は規格どおりとは限らない。「Unit ID 1 しか受け付けない」「何でも受け付ける」「0xFF だと応答しない」などばらばらなので、**最終的には機器のマニュアルに従う。**

## 0xFF が推奨される理由 (TCP 4.4.1.2)

> On TCP/IP, the MODBUS server is addressed using its IP address; therefore, the MODBUS Unit Identifier is useless. The value 0xFF has to be used.

ポイントは **0xFF はどのシリアル機器のアドレスにもなり得ない値** (248〜255 は予約) だということ。

防ぎたいのは、**IP の先にいる相手が、知らないうちに直結の機器からゲートウェイに変わっていた** ときの誤転送。
クライアント側は何も変えておらず、ずっと Modbus TCP で通信している。

```
最初:  192.168.0.20 = TCP 直結の温度計 A
       クライアントは (192.168.0.20, Unit ID = 1) で「レジスタ 10 に 500 を書く」を送っている
       → 温度計 A は Unit ID を無視して処理。問題なし

ある日: 温度計 A を撤去し、192.168.0.20 を TCP→RTU ゲートウェイに割り当て直した
       ゲートウェイの先には RS-485 でポンプ (スレーブ 1) がいる
       クライアントの設定は誰も直していない

結果:  Unit ID = 1  → ゲートウェイがスレーブ 1 へ転送 → ポンプのレジスタ 10 に 500 が書かれる (事故)
       Unit ID = 0xFF → シリアル上にいない番号なので転送しない → エラーになり、気づける
```

- 誤って動くより、確実に失敗するほうが安全という設計
- **0 がだめな理由**: 0 はシリアル側でブロードキャストなので、ゲートウェイの先の全スレーブに書き込みが届く。応答もないので失敗にも気づけない。最悪のケース
- 同じことは IP の設定ミスや DHCP の割り当て違いでも起こり得る
- 転送できないとき、ゲートウェイは例外 0x0A (Gateway Path Unavailable) か 0x0B (Gateway Target Device Failed to Respond) を返すのが一般的 (挙動は機種による)

たとえると「部屋番号が不要な一軒家宛てでも、部屋番号欄には存在しない番号を書いておく」。
空欄 (0) だとマンションに届いたときに全戸に配られてしまう。
