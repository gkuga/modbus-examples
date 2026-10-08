# Modbus 学習メモ

このリポジトリのサンプルを動かしながら調べたことのまとめ。
規格の節番号は modbus.org が公開している以下の文書のもの。

| 略称 | 文書 | 内容 |
| --- | --- | --- |
| Application | [MODBUS Application Protocol Specification V1.1b3](https://www.modbus.org/file/secure/modbusprotocolspecification.pdf) (2012) | PDU、データモデル、ファンクションコード |
| Serial | [MODBUS over Serial Line Specification and Implementation Guide V1.02](https://www.modbus.org/file/secure/modbusoverserial.pdf) (2006) | RTU / ASCII、スレーブアドレス、RS-485 |
| TCP | [MODBUS Messaging on TCP/IP Implementation Guide V1.0b](https://www.modbus.org/file/secure/messagingimplementationguide.pdf) (2006) | MBAP ヘッダ、Unit Identifier、ゲートウェイ |

一覧ページ: <https://modbus.org/modbus-specifications>

## 目次

1. [規格と階層構造](01-specifications.md) — 規格の構成、OSI 参照モデルとの対応、PDU と ADU、RTU と ASCII
2. [アドレス](02-addressing.md) — Slave Address と Unit Identifier、値の範囲、IP アドレスとの関係、0xFF が推奨される理由
3. [データモデル](03-data-model.md) — 4 つのテーブル、レジスタ、レジスタマップ、テーブルの重ね合わせ
4. [ファンクションコード](04-function-codes.md) — 範囲と分類、一覧、例外レスポンス、0x2B と Device Identification
5. [リクエストとレスポンス](05-request-response.md) — 1 対 1 の原則と例外、診断カウンタ、書き込みの確認方法
6. [pymodbus のメモ](06-pymodbus-notes.md) — このリポジトリで使っている pymodbus 3.15 の挙動と癖
