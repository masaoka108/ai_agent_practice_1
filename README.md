# AI Agent Practice

このプロジェクトは、AIエージェントを使用した実験的なプロジェクトです。

## 必要条件

- Docker
- Docker Compose
- OpenAI API Key

## セットアップと実行方法

1. リポジトリをクローンします：
```bash
git clone [リポジトリURL]
cd ai_agent_practice_1
```

2. OpenAI API Keyをセットします。
docker-compose.ymlにOPENAI_API_KEYにセットします。

2. Dockerイメージをビルドして実行：
```bash
# Dockerイメージのビルド
docker compose build

# コンテナの起動と実行
docker compose up
```

または、以下のコマンドでバックグラウンドで実行することもできます：
```bash
docker compose up -d
```

3. コンテナに入る
```bash
docker-compose run --rm app bash
```

4. コンテナ内でいずれかのファイルを実行

LungChainで試す場合
```bash
python main.py
```

LangGraphで試す場合
```bash
python main_lg.py
```




## プロジェクト構成

```
.
├── Dockerfile          # Dockerイメージの定義ファイル
├── README.md           # 本ドキュメント
├── docker-compose.yml  # Docker Compose設定ファイル
├── main.py            # メインアプリケーションファイル
├── requirements.txt    # Pythonパッケージの依存関係
└── agent_graph.png    # エージェントグラフの可視化
```

## 参照
こちらの内容に沿って実装しました。
https://qiita.com/YutaroOgawa2/items/cb5b1db9f07a1c4f3f54

## 注意事項

- 環境変数の設定が必要な場合は、`.env`ファイルを作成してください。
- 詳細なログは`docker compose logs`で確認できます。