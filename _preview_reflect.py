"""사색 카드 디자인만 따로 확인하는 미리보기 (인용/사상/각주 세 유형)."""
import pathlib
import sys
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from briefing.data import futurists
from briefing.models import Brief, Reflection
from briefing.render import html as render_html

parts = []
for offset in range(len(futurists.FUTURISTS)):
    name, who, kind, body, source, sit, note = futurists.pick(offset)
    b = Brief(generated_at=datetime.now() + timedelta(days=offset))
    b.reflection = Reflection(name=name, who=who, kind=kind, body=body,
                              source=source, sit=sit, note=note)
    page = render_html.render(b)
    start = page.index('<section class="reflect">')
    end = page.index("</section>", start) + len("</section>")
    parts.append(page[start:end])

# 헤드(스타일)만 재사용하고 본문은 사색 카드들로 채운다
shell = render_html.render(Brief(generated_at=datetime.now()))
head = shell[: shell.index('<div class="wrap">') + len('<div class="wrap">')]
out = head + "\n".join(parts) + "</div></body></html>"

path = pathlib.Path("report/preview-reflect.html")
path.write_text(out, encoding="utf-8")
print(f"{len(parts)}장 렌더 →", path)
