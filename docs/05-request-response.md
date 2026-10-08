# リクエストとレスポンス

## 原則: 1 対 1

- 通信を始めるのは **必ずクライアント (マスタ)**。サーバは聞かれたことに答えるだけ
- 1 つのリクエストに返るレスポンスは最大 1 つ (正常レスポンスか例外レスポンス)
- **例外レスポンスも 1 つのレスポンス** なので、エラーでも 1 対 1 は保たれる
- リクエストなしにサーバから送ってくることはない

## レスポンスが返らないケース

| ケース | 扱い |
| --- | --- |
| ブロードキャスト (シリアルのアドレス 0) | 全スレーブが実行するが誰も応答しない。書き込みだけに使える (Serial 2.1) |
| 自分宛てでないフレーム (シリアル) | 破棄する (Serial 2.5) |
| CRC / パリティエラー (シリアル) | 壊れたフレームは破棄され、応答しない |
| Listen Only Mode | FC 0x08 サブファンクション 0x0004 で「聞くだけ」にすると以降応答しない。このリクエスト自体も "No response is returned" (Application 6.8) |
| 機器の停止、断線、処理落ち | 単に応答が来ない |

- **例外レスポンス** = 届いたが処理できなかった
- **タイムアウト** = 届いたかどうかも分からない

pymodbus の `no_response_expected=True` は、ブロードキャストのように応答が来ないと分かっているリクエストで待たないための引数。

## TCP では順番どおりとは限らない

TCP 4.4.1.2:

> Normally, on MODBUS serial line a client must send one request at a time. ... On TCP/MODBUS, several requests can be sent without waiting for a confirmation to the same server.

- シリアル: 1 本の線を共有するので 1 往復ずつ
- TCP: 応答を待たずに複数送ってよく、サーバも並行して処理できる。**Transaction Identifier** で対応付ける (hello-tcp では `00 01`, `00 02`, ... と増えていく)
- それでもペアは 1 対 1。Device Identification の「続きは Next Object Id で再リクエスト」も、ペアが複数回続くだけ

## ポーリング

サーバから通知する手段がないので、**値の変化を知るにはクライアントが定期的に読みに行くしかない。**
BACnet には COV (Change of Value) 通知があり、値が変わると機器側から知らせてくれる。ここが大きな違い。

## 診断カウンタ (FC 0x08, Serial Line only)

FC 0x08 Diagnostics には通信統計のカウンタが並んでいる。数え始めは電源投入、通信の再起動 (0x0001)、カウンタクリア (0x000A) のいずれか以降。

| サブファンクション | 名前 | 数えるもの |
| --- | --- | --- |
| 0x000A | Clear Counters and Diagnostic Register | (カウンタを 0 に戻す) |
| 0x000B | Bus Message Count | 線上で見たメッセージの総数 (他のスレーブ宛ても含む) |
| 0x000C | Bus Communication Error Count | CRC エラーの数 |
| 0x000D | Bus Exception Error Count | 自分が返した例外レスポンスの数 |
| 0x000E | Server Message Count | 自分宛て (ブロードキャストを含む) に処理したメッセージの数 |
| 0x000F | Server No Response Count | 自分宛てだが応答しなかった数 |
| 0x0010 | Server NAK Count | NAK 例外 (07、古いコード) を返した数 |
| 0x0011 | Server Busy Count | Busy 例外 (06) を返した数 |
| 0x0012 | Bus Character Overrun Count | 受信が処理に追いつかず取りこぼした数 |

### Server No Response Count (0x000F)

Application 6.8:

> The response data field returns the quantity of messages addressed to the remote device for which it has returned no response (neither a normal response nor an exception response), since its last restart, clear counters operation, or power-up.

```
リクエスト: 08 | 00 0f | 00 00
レスポンス: 08 | 00 0f | 00 05     ← 5 回
```

増えるのは **自分宛てとして受け取ったうえで、規格に従って黙った** とき (ブロードキャスト、Listen Only Mode 中)。
CRC エラーや他のスレーブ宛てのフレームでは増えない (そもそも自分宛てか判断できない / 自分宛てではない)。

### No Response Count では「届いたか」を把握できない

| クライアントから見た状況 | 本当の原因 | No Response Count |
| --- | --- | --- |
| 応答が来ない | ブロードキャスト / Listen Only Mode で意図的に黙った | 増える |
| 応答が来ない | リクエストが途中で壊れた (CRC エラー) | 増えない |
| 応答が来ない | リクエストは届いて処理されたが、**レスポンスが途中で壊れた** | 増えない (サーバは応答した認識) |
| 応答が来ない | 断線、機器の停止 | 増えない |

- 3 行目のように、書き込みは実行されたのにカウンタは増えない。「増えていない = 届いていない」とは言えない
- 合計の回数なので、どのリクエストか分からない。再起動で 0 に戻る
- Listen Only Mode 中はカウンタを読むリクエストにも応答しない
- FC 0x08 は Serial Line only。未対応のシリアル機器も多く、TCP 機器ではほぼ使えない

### Get Comm Event Counter (FC 0x0B, Application 6.9)

目的に近いのはこちら:

> By fetching the current count before and after a series of messages, a client can determine whether the messages were handled normally by the remote device.

「正常に処理できたメッセージの数」を数え、前後で読んで差を見るのが規格の想定どおりの使い方。
例外レスポンス、ポーリング、このカウンタ自体の読み出しは数えない。これも Serial Line only。

カウンタ類の使いどころは **線全体の健康診断** (通信トラブルの切り分け):

- Bus Communication Error Count が増えている → ノイズ、配線、ボーレートの不一致
- No Response Count が増えている → 届いているのに答えていない。Listen Only Mode を疑う
- どれも増えていない → 信号が届いていない (断線など)

## 書き込みを確認する実務の方法

個々のリクエストが届いたかは **読み戻しで確認する** のが確実。

```python
client.write_register(0, 500, device_id=1)                      # 書く
value = client.read_holding_registers(0, count=1, device_id=1)  # 読み戻す
assert value.registers[0] == 500                                # 反映されたか
```

- 普通の書き込み: レスポンス (エコー) が返れば届いている。返らなかったら読み戻して判断する
- ブロードキャスト: 応答がないので各スレーブを個別に読み戻す
- リトライ: 同じ値を書くだけなら二重に実行しても結果は同じなので安全。
  「リセット」のように 1 回の実行で状態が変わる操作は、読み戻してから再送するか決める
  (power-meter の積算電力量リセットがこの例)
- クライアントはレスポンスが例外かどうかを必ず確認する。pymodbus は例外レスポンスでも例外を投げないので、
  `response.isError()` を見ないと失敗に気づけない (power-meter の `check()`)
