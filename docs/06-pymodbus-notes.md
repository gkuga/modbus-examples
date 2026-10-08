# pymodbus のメモ (3.15.0)

このリポジトリで使っている pymodbus 3.15.0 の挙動。規格とずれているところもあるので注意。

## API の変遷

- 引数名: `slave=` → `device_id=` (3.10 以降)
- サーバのデータ定義: `ModbusSequentialDataBlock` / `ModbusDeviceContext` / `ModbusServerContext` は非推奨 (v4 で削除予定)。
  新しい API は `SimData` / `SimDevice`
- 古い API にはアドレスが 1 ずれる癖がある (データブロックのアドレス N+1 がプロトコル上のアドレス N)。新しい API にはない

## SimDevice と SimData

```python
SimDevice(
    id=1,                    # この Device ID 宛てに答える
    simdata=[
        SimData(0, values="Hello, Modbus!", datatype=DataType.STRING),  # アドレス 0〜6
        SimData(7, count=10, values=0, datatype=DataType.UINT16),       # アドレス 7〜16
    ],
)
```

- `SimData` は「アドレス X からこういう値が並んでいる」というブロック。文字列は 2 文字ずつ 16 bit に詰められる
- 定義していないアドレスは例外 02
- `count` と `values` のリストを両方指定すると、リストが `count` 回繰り返される (`count=2, values=[1000, 0]` は 4 レジスタ)
- 32 bit 型 (INT32, FLOAT32 など) は常に上位ワードが先。下位ワードが先の値は自分で変換して `UINT16` のリストで置く

### 共有ブロックと 4 ブロック

- `simdata` に **リスト** を渡す → 4 テーブルが 1 つの領域を共有 (hello-tcp)。Input Registers を読んでも Holding Registers と同じ値が返る
- `simdata` に **4 つのリストのタプル** `(coils, discrete inputs, holding registers, input registers)` を渡す → 別々 (power-meter)。
  coils / discrete inputs は `DataType.BITS` のみ。空リストは不可

ビットは内部で 16 bit ずつ 1 レジスタに詰められている (bit 0 = 最下位ビット = 若い番号)。

### action フック

`SimDevice(action=...)` に async 関数を渡すと、レジスタへのアクセスのたびに呼ばれる。

```python
async def on_access(function_code, start_address, address, count, registers, values):
    ...
```

- `registers` をその場で書き換えると、今回と以降のレスポンスに反映される (計測値のシミュレーションに使える)
- `values` は書き込みの値 (読み出しでは `None`)
- **書き込みの後、レスポンスを作るために同じ FC (0x05, 0x06 など) で `values=None` の読み戻しが呼ばれる。**
  これを書き込みとして扱うと例外になり、サーバは例外 04 を返す (値自体は書き込まれているので気づきにくい)
- FC 0x06 の正常レスポンスはエコーなので、`values` を書き換えると規格から外れたレスポンスになる

## Device ID の扱い

- 範囲チェックは 0〜255 だけ。RTU で 248 以上を指定してもエラーにならない。規格どおりの値を選ぶのは使う側の責任
- `SimDevice(id=0)` は「定義していない全 ID に答えるデバイス」という pymodbus 独自の意味。シリアルのブロードキャストとは別物
- **存在しない Device ID 宛てのリクエストに、規格どおり無視せず例外 04 を返す。**
  内部で `KeyError` になり、`ignore_missing_devices=True` でも変わらない (RTU でも TCP でも同じ)

## Read Device Identification

`SimDevice(identity=ModbusDeviceIdentification(...))` を設定しないと、
Conformity level 0x83 を返しながらオブジェクトを 0 個返す (Basic は必須なので規格違反)。

```python
from pymodbus.pdu.device import ModbusDeviceIdentification

identity = ModbusDeviceIdentification(info_name={
    "VendorName": "gkuga", "ProductCode": "HM-1", "MajorMinorRevision": "1.0",
})
```

## クライアント

- 例外レスポンスでも Python の例外は投げない。`response.isError()` で確認する
- `trace_packet=` に関数を渡すと送受信の生バイト列を見られる (このリポジトリのサンプルで使用)
- `convert_from_registers` / `convert_to_registers` で INT32, FLOAT32, STRING などに変換できる。`word_order` でワードオーダーを指定
- `read_device_information(read_code=..., object_id=...)` が 0x2B / 0x0E

## 仮想シリアル (pty)

hello-rtu の `virtual_serial.py` は pty のペアで仮想ケーブルを作る。pty はボーレートを無視するので、
ボーレート不一致の実験は実機でしかできない。
