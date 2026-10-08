# modbus-examples

Modbus を学ぶためのサンプル集。Python + [pymodbus](https://github.com/pymodbus-dev/pymodbus) を使う。
各サンプルは [uv](https://docs.astral.sh/uv/) で管理していて、ディレクトリ内で `make install` (`uv sync`) すれば動く。

仕組みの解説は [docs](docs/README.md) にまとめている。

| ディレクトリ | 内容 |
| --- | --- |
| [hello-tcp](hello-tcp) | Modbus TCP の hello world |
| [hello-rtu](hello-rtu) | Modbus RTU の hello world（仮想シリアルポートで実機なしに動く） |
| [power-meter](power-meter) | 架空の電力計。レジスタマップに沿って倍率・符号付き・32 bit の値を解釈する |

hello-tcp と hello-rtu はどちらも同じことをする:

1. サーバ（スレーブ）の保持レジスタ 0-6 に `"Hello, Modbus!"` を入れておく（1 レジスタ = 16bit = 2 文字）
2. クライアント（マスタ）が Read Holding Registers (0x03) で読み出して文字列に戻す
3. Write Single Register (0x06) でレジスタ 10 に 42 を書き、読み戻す

送受信したフレームを hex で表示するので、TCP と RTU でフレームがどう違うかを見比べられる。
