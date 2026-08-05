import requests
import trafilatura

REQUEST_TIMEOUT = 30


def web_fetch(url: str) -> str:
    """获取静态网页并转换为 Markdown。网页转 Markdown 后的消息不一定完整或准确；此工具只能获取静态页面，无法执行 JavaScript 或获取动态渲染内容。

    Args:
        url: 要获取的网页 URL
    """
    downloaded = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text
    markdown = trafilatura.extract(
        downloaded,
        output_format="markdown",
        include_formatting=True,   # 关键:保留代码块等结构
        include_tables=True,
    )
    return markdown or "Error: no extractable content"