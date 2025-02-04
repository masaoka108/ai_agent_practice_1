# LungGraphのサンプルコード

from duckduckgo_search import DDGS
from itertools import islice
from langchain.tools import tool
from pydantic import BaseModel
import requests
from readability import Document
import html2text

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate
from langchain_openai import ChatOpenAI


from langgraph.prebuilt import create_react_agent
# from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate
from langchain_core.messages import AnyMessage

from IPython.display import Image, display

class SearchDDGInput(BaseModel):
    query: str
    max_result_num: int = 5

class FetchPageInput(BaseModel):
    url: str
    page_num: int = 0
    timeout_sec: int = 10

@tool(args_schema=SearchDDGInput)
def search_ddg(query, max_result_num=5):
    """
    ## Toolの説明
    本ToolはDuckDuckGoを利用し、Web検索を実行するためのツールです。

    ## Toolの動作方法
    1. userが検索したいキーワードに従ってWeb検索します
    2. assistantは以下の戻り値の形式で検索結果をuserに回答します

    ## 戻り値の形式

    Returns
    -------
    List[Dict[str, str]]:
    - title
    - snippet
    - url
    """

    # [1] Web検索を実施
    res = DDGS().text(query, region='jp-jp', safesearch='off', backend="lite")

    # [2] 結果のリストを分解して戻す
    return [
        {
            "title": r.get('title', ""),
            "snippet": r.get('body', ""),
            "url": r.get('href', "")
        }
        for r in islice(res, max_result_num)
    ]


@tool(args_schema=FetchPageInput)
def fetch_page(url, page_num=0, timeout_sec=10):
    """
    ## Toolの説明
    本Toolは指定されたURLのWebページから本文の文章を取得するツールです。
    詳細な情報を取得するのに役立ちます

    ## Toolの動作方法
    1. userがWebページのURLを入力します
    2. assistantはHTTPレスポンスステータスコードと本文の文章内容をusrに回答します

    ## 戻り値の設定
    Returns
    -------
    Dict[str, Any]:
    - status: str
    - page_content
      - title: str
      - content: str
      - has_next: bool
    """

    # [1] requestモジュールで指定URLのＷebページ全体を取得
    try:
        response = requests.get(url, timeout=timeout_sec)
        response.encoding = 'utf-8'
    except requests.exceptions.Timeout:
        return {
            "status": 500,
            "page_content": {'error_message': 'Could not download page due to Timeout Error. Please try to fetch other pages.'}
        }

    # [2] HTTPレスポンスステータスコードが200番でないときにはエラーを返す
    if response.status_code != 200:
        return {
            "status": response.status_code,
            "page_content": {'error_message': 'Could not download page. Please try to fetch other pages.'}
        }

    # [3] 本文取得の処理へ（書籍ではtry-exceptできちんとしていますが、簡易に）
    doc = Document(response.text)
    title = doc.title()
    html_content = doc.summary()
    content = html2text.html2text(html_content)

    # [4] 本文の冒頭を取得
    chunk_size = 1000*3  #【chunk_sizeを大きくしておきます】
    content = content[:chunk_size]

    # [5] return処理
    return {
        "status": 200,
        "page_content": {
            "title": title,
            "content": content,  # chunks[page_num], を文書分割をやめて、contentにします
            "has_next": False  # page_num < len(chunks) - 1
        }
    }



# ----エージェント実装 start----

CUSTOM_SYSTEM_PROMPT = """
## あなたの役割
あなたの役割はuserの入力する質問に対して、インターネットでWebページを調査をし、回答することです。

## あなたが従わなければいけないルール
1. 回答はできるだけ短く、要約して回答してください
2. 文章が長くなる場合は改行して見やすくしてください
3. 回答の最後に改行した後、参照したページのURLを記載してください
"""


# プロンプトを定義
prompt = ChatPromptTemplate.from_messages([
    ("system", CUSTOM_SYSTEM_PROMPT),  # [3] で定義したのと同じシステムプロンプトです
    ("user", "{messages}")
    # MessagesPlaceholder(variable_name="agent_scratchpad")  # agent_scratchpadは中間生成物の格納用でしたが、LangGraphでは不要です
])

# LangGraphではGraph構造で全体を処理するので、stateを変化させノードが移るタイミングで、promptを（会話やAgentの自分メモ）を進めるように定義します
def _modify_messages(messages: list[AnyMessage]):
    return prompt.invoke({"messages": messages}).to_messages()

# ReactAgentExecutorの準備
# modelとtoolsは[3]と同じものを使用します
tools = [search_ddg, fetch_page]
llm = ChatOpenAI(temperature=0, model_name="gpt-4o")
# 【2024年8月3日現在では、modelにgpt-4o-miniを使用すると日本語ではうまく動作してくれません】そのため、gpt-4oを使用

web_browsing_agent = create_react_agent(llm, tools, state_modifier=_modify_messages)
# 変数名はgraphや、appを使用しているケースもあります


# [1] 質問文章
query_ddg = "2024年全豪オープンテニスの男子シングルスって誰が優勝した？各セットのポイントも教えてください"

# # [2]ステップの段階的出力（一度でinvokeする流れはこの後で実行します。veboseがなく、動作が分かりにくいので）
# for step in web_browsing_agent.stream({"messages": [("user", query_ddg)]}, stream_mode="updates"):
#     print(step)

# [3] エージェントをinvokeで実行（invokeのあとの変数の入れ方が少し異なります）
messages = web_browsing_agent.invoke({"messages": [("user", query_ddg)]})
# 変数名はresponseではなく、messagesが使用されます

# [4] 質問と回答を表示
# ==================
for i in range(len(messages["messages"])):
    if messages["messages"][i].type == "tool":
        pass  # toolの出力は除外
    elif messages["messages"][i].type == "human":
        print("human: ", messages["messages"][i].content)
    elif messages["messages"][i].type == "ai" and len(messages["messages"][i].content) > 0:
        # AIがtool使用の命令ではなく、文章生成をしている場合は出力
        print("AI: ", messages["messages"][i].content)



# # 画像をファイルとして保存（絶対パスを使用）
# graph = web_browsing_agent.get_graph()
# # グラフをGraphviz DOT形式に変換
# import graphviz
# dot = graphviz.Digraph()
# for node in graph.nodes:
#     dot.node(str(node))
# for edge in graph.edges:
#     dot.edge(str(edge[0]), str(edge[1]))
# # PNGとして保存
# dot.render("/app/agent_graph", format="png", cleanup=True)

