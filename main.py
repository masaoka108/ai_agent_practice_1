# LungChainのサンプルコード

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


def create_agent():
    # [1]、[2]で定義したAgentが使用可能なToolを指定します
    tools = [search_ddg, fetch_page]

    # プロンプトを与えます。ChatPromptTemplateの詳細は書籍本体の解説をご覧ください。
    # 重要な点は、最初のrole "system"に上記で定義したCUSTOM_SYSTEM_PROMPTを与え、
    # userの入力は{input}として動的に埋め込むようにしている点です
    # agent_scratchpadはAgentの動作の途中経過を格納するためのものです
    prompt = ChatPromptTemplate.from_messages([
        ("system", CUSTOM_SYSTEM_PROMPT),
        # MessagesPlaceholder(variable_name="chat_history"),  # チャットの過去履歴はなしにしておきます
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    # 使用するLLMをOpenAIのGPT-4o-miniにします（GPT-4だとfechなしに動作が完了してしまう）
    llm = ChatOpenAI(temperature=0., model_name="gpt-4o-mini")

    # Agentを作成
    agent = create_tool_calling_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,  # これでAgentが途中でToolを使用する様子が可視化されます
        # memory=st.session_state['memory']  # memory≒会話履歴はなしにしておきます
    )

# [1] Agentを作成
web_browsing_agent = create_agent()

# [2] 質問文章
query_ddg = "OpenAIのDeep Researchの利用例を教えて"

# [3] エージェントを実行
response = web_browsing_agent.invoke(
    {'input': query_ddg},  # userの入力に上記の質問を入れる
)



# ----エージェント実装 end----



# ----人力チェック2 start----

# # URLを指定
# # url_hit = "https://www.sponichi.co.jp/sports/news/2024/01/29/kiji/20240129s00028000133000c.html"
# url_hit = "https://ja.wikipedia.org/wiki/2024年全豪オープン"


# # 実行
# result = fetch_page.invoke({"url": url_hit})
# print(result)

# ----人力チェック2 end----



# ----人力チェック1 start----

# # [1] 検索文章
# query_ddg = "2024年全豪オープンテニスの男子シングルスって誰が優勝した？"

# # [2] DuckDuckGoを人力で動かして？、検索
# res = DDGS().text(query_ddg, region='jp-jp', safesearch='off', backend="lite")

# # [3] 検索結果を一つずつ取得して表示
# for result in res:
#     print(result)

# ----人力チェック1 end----
