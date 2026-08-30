"""'내일의 기술' 25편 전체를 한 페이지에서 훑어보는 미리보기."""
import pathlib, sys
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from briefing.data import futures
from briefing.models import Brief, FutureChapter
from briefing.render import html as render_html

parts = []
for offset in range(len(futures.CHAPTERS)):
    ch, n, total = futures.pick(offset)
    b = Brief(generated_at=datetime.now() + timedelta(days=offset))
    b.future = FutureChapter(part=ch.part, title=ch.title, subtitle=ch.subtitle,
                             horizon=ch.horizon, body=ch.body, voices=ch.voices,
                             counter=ch.counter, where=ch.where, number=n, total=total)
    page = render_html.render(b)
    start = page.index('<section class="reflect book">')
    end = page.index("</section>", start) + len("</section>")
    parts.append(page[start:end])

shell = render_html.render(Brief(generated_at=datetime.now()))
head = shell[: shell.index('<div class="wrap">') + len('<div class="wrap">')]
out = pathlib.Path("report/preview-book.html")
out.write_text(head + "\n".join(parts) + "</div></body></html>", encoding="utf-8")
print(f"{len(parts)}편 렌더 →", out)
