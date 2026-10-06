# hello-tcp

Modbus TCP の hello world。

## 実行

```sh
make install
make run-server   # ターミナル 1
make run-client   # ターミナル 2
```

## 出力例

```
Read holding registers 0-6 (function code 0x03)
  TX: 00 01 00 00 00 06 01 03 00 00 00 07
  RX: 00 01 00 00 00 11 01 03 0e 48 65 6c 6c 6f 2c 20 4d 6f 64 62 75 73 21
  registers: [18533, 27756, 28460, 8269, 28516, 25205, 29473]
  decoded:   'Hello, Modbus!'
```

## フレームの読み方

Modbus TCP のフレームは **MBAP ヘッダ (7 byte) + PDU**。

```
00 01 | 00 00 | 00 06 | 01 | 03 | 00 00 00 07
 |       |       |      |    |    └ PDU データ: 開始アドレス 0x0000, 個数 7
 |       |       |      |    └ ファンクションコード 0x03 (Read Holding Registers)
 |       |       |      └ Unit ID (デバイス ID)
 |       |       └ 後続バイト数 (Unit ID + PDU = 6)
 |       └ プロトコル ID (Modbus は常に 0)
 └ トランザクション ID (リクエストとレスポンスの対応付けに使う。毎回 +1 される)
```

レスポンスの PDU は `03 0e 48 65 ...` = ファンクションコード, バイト数 14, データ。
`48 65` = `'H' 'e'` = 0x4865 = 18533 が最初のレジスタ。

TCP 自体に誤り検出があるので、RTU のような CRC は付かない。
