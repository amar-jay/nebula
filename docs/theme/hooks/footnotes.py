from mkdocs.structure.pages import Page
from mkdocs.plugins import event_priority

@event_priority(-100)
def on_page_markdown(markdown: str, /, *, page: Page, config, files) -> str | None:
  if not page.meta.get("footnotes"):
    return
  
  return f"{markdown}\n{CONTENT}"

CONTENT: str = """
----
<h2 id="__footnotes">
  <span class="twemoji">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path d="M8.75 5.5h11.5a.75.75 0 0 1 0 1.5H8.75a.75.75 0 0 1 0-1.5Zm0 6h11.5a.75.75 0 0 1 0 1.5H8.75a.75.75 0 0 1 0-1.5Zm0 6h11.5a.75.75 0 0 1 0 1.5H8.75a.75.75 0 0 1 0-1.5ZM5 12a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM4 7a1 1 0 1 1 0-2 1 1 0 0 1 0 2Zm0 12a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"></path></svg>
  </span>
  Footnotes
</h2>

<!-- footnotes -->
"""