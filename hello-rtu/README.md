# hello-rtu

Modbus RTU の hello world。

実機の RS-485 がなくても動くように、`virtual_serial.py` で仮想のシリアルケーブル
（pty のペア）を作り、`ttyV0`（サーバ側）と `ttyV1`（クライアント側）をつなぐ。

## 実行

```sh
make install
make run-serial   # ターミナル 1: ./ttyV0 <-> ./ttyV1 を作る
make run-server   # ターミナル 2: ttyV0 で待ち受け (9600bps 8N1, device id 1)
make run-client   # ターミナル 3: ttyV1 から読み書き
```

実機 (USB-RS485 変換器など) を使う場合は `server.py` / `client.py` の `PORT` を
`/dev/tty.usbserial-XXXX` などに変える。

## 出力例

```
Read holding registers 0-6 (function code 0x03)
  TX: 01 03 00 00 00 07 04 08
  RX: 01 03 0e 48 65 6c 6c 6f 2c 20 4d 6f 64 62 75 73 21 88 b7
  registers: [18533, 27756, 28460, 8269, 28516, 25205, 29473]
  decoded:   'Hello, Modbus!'
```

## フレームの読み方

Modbus RTU のフレームは **スレーブアドレス (1 byte) + PDU + CRC (2 byte)**。

```
01 | 03 | 00 00 00 07 | 04 08
 |    |    |             └ CRC-16 (下位バイトが先)
 |    |    └ 開始アドレス 0x0000, 個数 7
 |    └ ファンクションコード 0x03 (Read Holding Registers)
 └ スレーブアドレス (デバイス ID)
```

## TCP との違い

| | TCP | RTU |
| --- | --- | --- |
| ヘッダ | MBAP (7 byte, トランザクション ID・長さを含む) | スレーブアドレス 1 byte だけ |
| 誤り検出 | なし (TCP に任せる) | CRC-16 |
| フレームの区切り | 長さフィールド | 3.5 文字分の無通信時間 |
| 同時リクエスト | トランザクション ID で区別できる | 1 本の線を共有するので 1 往復ずつ |

PDU 部分 (`03 00 00 00 07`) はどちらも同じ。

試してみると面白いこと:

- `client.py` の `DEVICE_ID` を 2 にする → 仕様上、RTU のスレーブは自分宛てでないフレームを無視するので
  クライアントはタイムアウトするはず。ただし pymodbus 3.15 の `SimDevice` は未知の ID にも
  例外レスポンス `02 83 04 b0 f3` を返す (ファンクションコード 0x03 | 0x80 = 0x83, 例外コード 0x04 = Server Device Failure)。
  例外レスポンスのフレームを観察する例として見るとよい
- (実機のみ) 片方だけ `BAUDRATE` を変える → 文字化けして CRC が合わず通信できない。
  仮想シリアル (pty) はボーレートを無視するので再現しない
