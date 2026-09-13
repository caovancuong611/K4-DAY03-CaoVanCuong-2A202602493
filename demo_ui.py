"""
💬 CHAT UI — VinUni Academic ReAct Agent (Apple-style chatbot)
Chạy: python -m streamlit run demo_ui.py   (đứng ở thư mục gốc dự án)
"""

import io
import json
import sys
import html
import inspect
import contextlib
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

import providers as providers_mod              # noqa: E402
from app import run_react_agent                # noqa: E402
from tools import TOOLS_SCHEMA, MOCK_DATABASE  # noqa: E402
from mcp_server import MCPAcademicServer       # noqa: E402

TRACE_FILE = ROOT / "docs" / "trace_waterfall.json"

st.set_page_config(page_title="Trợ lý Học vụ", page_icon="🎓", layout="centered")

# ═══════════════════════════ Apple-style chat design ═══════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

:root{
  --ink:#1D1D1F; --ink2:#6E6E73; --ink3:#86868B;
  --line:#E8E8ED; --surface:#FFFFFF; --canvas:#FBFBFD;
  --blue:#0071E3; --bubble:#F1F1F4;
  --green:#30A46C; --amber:#B25E09; --purple:#6E56CF;
}

html, body, [class*="css"], .stApp{
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Inter","Helvetica Neue",sans-serif !important;
  -webkit-font-smoothing:antialiased;
}
.stApp{ background:var(--canvas); }
#MainMenu, footer, header{ visibility:hidden; }
.block-container{ padding-top:2.2rem; padding-bottom:7rem; max-width:780px; }

/* ── Header ── */
.hdr{ text-align:center; margin-bottom:26px; }
.hdr-avatar{
  width:56px; height:56px; border-radius:50%; margin:0 auto 12px;
  background:linear-gradient(145deg,#0071E3,#6E56CF);
  display:flex; align-items:center; justify-content:center; font-size:26px;
  box-shadow:0 4px 14px rgba(0,113,227,.22);
}
.hdr-name{ font-size:21px; font-weight:600; letter-spacing:-.02em; color:var(--ink); }
.hdr-sub{ font-size:13px; color:var(--ink3); margin-top:3px; }
.hdr-pill{
  display:inline-flex; align-items:center; gap:6px; margin-top:11px;
  padding:5px 12px; border-radius:980px; font-size:12px; font-weight:500;
}
.pill-live{ background:#E9F7EF; color:#1B7F4C; }
.pill-mock{ background:#FEF3E2; color:#8A4B00; }
.pill-err { background:#FDEBEC; color:#B42318; }

/* ── Bubbles ── */
.row{ display:flex; margin-bottom:12px; }
.row-user{ justify-content:flex-end; }
.row-bot{ justify-content:flex-start; }

.bubble{
  max-width:76%; padding:12px 17px; font-size:15.5px; line-height:1.52;
  letter-spacing:-.01em; word-break:break-word;
}
.b-user{
  background:var(--blue); color:#fff;
  border-radius:20px 20px 5px 20px;
}
.b-bot{
  background:var(--surface); color:var(--ink); border:1px solid var(--line);
  border-radius:20px 20px 20px 5px; box-shadow:0 1px 2px rgba(0,0,0,.04);
}

/* ── Reasoning panel ── */
.reason-wrap{ margin:-4px 0 16px 0; }
.step{
  display:flex; gap:11px; align-items:flex-start;
  padding:10px 2px; border-bottom:1px solid #F0F0F3;
}
.step:last-child{ border-bottom:none; }
.dot{ width:7px; height:7px; border-radius:50%; margin-top:6px; flex-shrink:0; }
.d-thought{ background:var(--purple); }
.d-action { background:var(--amber); }
.d-obs    { background:var(--ink3); }
.d-final  { background:var(--green); }
.d-warn   { background:#E5484D; }
.s-kind{
  font-size:10.5px; font-weight:600; letter-spacing:.05em;
  text-transform:uppercase; color:var(--ink3); margin-bottom:3px;
}
.s-body{ font-size:14px; line-height:1.5; color:var(--ink); }
.s-body.mono{
  font-family:"SF Mono",ui-monospace,Menlo,monospace; font-size:12px;
  color:var(--ink2); background:#F5F5F7; padding:8px 10px; border-radius:9px;
}
.loop-tag{
  font-size:10.5px; font-weight:600; letter-spacing:.06em; text-transform:uppercase;
  color:var(--blue); margin:14px 0 4px 0;
}

/* ── Suggestion chips ── */
.stButton > button{
  background:var(--surface) !important; color:var(--ink) !important;
  border:1px solid var(--line) !important; border-radius:980px !important;
  padding:8px 16px !important; font-size:13.5px !important; font-weight:450 !important;
  box-shadow:none !important; width:100% !important; transition:all .18s ease !important;
}
.stButton > button:hover{ border-color:#C7C7CC !important; background:#FAFAFC !important; }

/* ── Chat input ── */
[data-testid="stChatInput"]{
  background:var(--surface) !important; border:1px solid var(--line) !important;
  border-radius:24px !important; box-shadow:0 2px 12px rgba(0,0,0,.06) !important;
}
[data-testid="stChatInput"] textarea{ font-size:15px !important; color:var(--ink) !important; }
[data-testid="stBottomBlockContainer"]{ background:transparent !important; }

details{
  background:transparent !important; border:none !important;
  border-left:2px solid var(--line) !important; border-radius:0 !important;
  padding-left:14px !important; margin:2px 0 14px 4px !important;
}
details summary{
  font-size:12.5px !important; font-weight:500 !important; color:var(--ink3) !important;
}
section[data-testid="stSidebar"]{ background:var(--surface); border-right:1px solid var(--line); }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════ Provider discovery ═══════════════════════════
FACTORY_NAMES = ("get_llm_provider", "get_provider", "create_provider",
                 "build_provider", "load_provider", "make_provider")


@st.cache_resource
def build_provider():
    for name in FACTORY_NAMES:
        fn = getattr(providers_mod, name, None)
        if callable(fn):
            try:
                return fn()
            except TypeError:
                continue
    for name in dir(providers_mod):
        if name.endswith("Provider") and not name.startswith(("_", "Base")):
            cls = getattr(providers_mod, name)
            if inspect.isclass(cls):
                try:
                    return cls()
                except TypeError:
                    continue
    raise RuntimeError("Không tìm thấy factory provider trong src/providers.py")


def call_agent(query, provider, mcp):
    kwargs = {}
    for name in inspect.signature(run_react_agent).parameters:
        low = name.lower()
        if low in ("query", "user_input", "question", "user_query", "prompt", "text"):
            kwargs[name] = query
        elif "provider" in low or low in ("llm", "client", "model"):
            kwargs[name] = provider
        elif "mcp" in low or "server" in low:
            kwargs[name] = mcp
    return run_react_agent(**kwargs)


mcp_server = MCPAcademicServer()
try:
    provider = build_provider()
    provider_label = type(provider).__name__
    is_live = "mock" not in provider_label.lower()
    provider_ok, provider_error = True, None
except Exception as exc:  # noqa: BLE001
    provider, provider_label, is_live = None, "—", False
    provider_ok, provider_error = False, exc


# ═══════════════════════════ Log parsing ═══════════════════════════
KIND = {
    "🧠": ("Suy nghĩ", "d-thought", False),
    "🛠": ("Gọi công cụ", "d-action", True),
    "👁": ("Kết quả từ MCP", "d-obs", True),
    "🏁": ("Trả lời", "d-final", False),
    "⚠": ("Cảnh báo", "d-warn", False),
}


def parse_log(raw: str):
    """Tách log thành (danh sách bước, câu trả lời cuối)."""
    steps, answer = [], ""
    for line in raw.splitlines():
        s = line.strip()
        if not s or set(s) <= {"=", "-"}:
            continue
        if s.startswith("---") and "Step" in s:
            steps.append(("loop", s.strip("- ").strip(), "", False))
            continue
        for prefix, (kind, dot, mono) in KIND.items():
            if s.startswith(prefix):
                body = s[len(prefix):].lstrip("️ :")
                if body.startswith("["):
                    tail = body.split("]:", 1)
                    body = tail[1].strip() if len(tail) > 1 else body
                if dot == "d-final":
                    answer = body
                steps.append((dot, kind, body, mono))
                break
    return steps, (answer or "Agent không trả về câu trả lời cuối.")


def render_reasoning(steps):
    parts = ['<div class="reason-wrap">']
    for dot, kind, body, mono in steps:
        if dot == "loop":
            parts.append(f'<div class="loop-tag">{html.escape(kind)}</div>')
            continue
        cls = " mono" if mono else ""
        parts.append(
            f'<div class="step"><div class="dot {dot}"></div><div style="flex:1;">'
            f'<div class="s-kind">{kind}</div>'
            f'<div class="s-body{cls}">{html.escape(body)}</div></div></div>'
        )
    parts.append("</div>")
    return "".join(parts)


# ═══════════════════════════ Sidebar ═══════════════════════════
with st.sidebar:
    st.markdown('<div style="font-size:17px;font-weight:600;color:#1D1D1F;">Trợ lý Học vụ</div>'
                '<div style="font-size:12px;color:#86868B;margin:2px 0 18px;">'
                'ReAct Agent · MCP Server</div>', unsafe_allow_html=True)

    st.caption(f"**{len(mcp_server.list_tools())}** tools qua MCP · "
               f"**{len(MOCK_DATABASE)}** sinh viên trong CSDL")

    for tool in TOOLS_SCHEMA:
        with st.expander(tool["name"]):
            st.caption(tool["description"])
            st.json(tool["parameters"], expanded=False)

    with st.expander("Dữ liệu học vụ"):
        st.json(MOCK_DATABASE, expanded=False)

    if TRACE_FILE.exists():
        with st.expander("Waterfall trace"):
            data = json.loads(TRACE_FILE.read_text(encoding="utf-8"))
            events = data if isinstance(data, list) else data.get("events", data)
            st.json(events[-6:] if isinstance(events, list) else events, expanded=False)

    st.divider()
    if st.button("Xóa hội thoại"):
        st.session_state.messages = []
        st.rerun()


# ═══════════════════════════ Header ═══════════════════════════
if provider_ok:
    pill_cls, pill_txt = ("pill-live", f"Live · {provider_label}") if is_live \
        else ("pill-mock", f"Offline · {provider_label}")
else:
    pill_cls, pill_txt = "pill-err", str(provider_error)

st.markdown(
    f'<div class="hdr">'
    f'  <div class="hdr-avatar">🎓</div>'
    f'  <div class="hdr-name">Trợ lý Học vụ VinUni</div>'
    f'  <div class="hdr-sub">Tra cứu hồ sơ · GPA · Đặt lịch cố vấn</div>'
    f'  <div class="hdr-pill {pill_cls}">● {html.escape(pill_txt)}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ═══════════════════════════ Chat state ═══════════════════════════
if "messages" not in st.session_state:
    st.session_state.messages = []

SUGGESTIONS = [
    ("Tra cứu hồ sơ SV2026001", "Hãy tra cứu thông tin học vụ của sinh viên SV2026001."),
    ("Đặt lịch cố vấn", "Tôi là sinh viên SV2026001, muốn đặt lịch tư vấn học vụ với PGS.TS Nguyễn Văn A vào lúc 14:00 ngày 15/09/2026."),
    ("Suy luận 2 bước ★", "Cố vấn học tập của sinh viên SV2026002 là ai? Hãy đặt lịch tư vấn với thầy/cô đó vào lúc 09:00 ngày 16/09/2026 giúp tôi."),
    ("Mã không tồn tại", "Cho tôi xem thông tin học vụ và GPA của sinh viên SV9999999."),
]

pending = None
if not st.session_state.messages:
    st.markdown('<div style="font-size:12px;color:#86868B;text-align:center;margin-bottom:10px;">'
                'Thử một câu hỏi</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    for i, (label, text) in enumerate(SUGGESTIONS):
        with (c1 if i % 2 == 0 else c2):
            if st.button(label, key=f"sug{i}"):
                pending = text

# ── Lịch sử hội thoại ──
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="row row-user"><div class="bubble b-user">'
                    f'{html.escape(msg["content"])}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="row row-bot"><div class="bubble b-bot">'
                    f'{html.escape(msg["content"])}</div></div>', unsafe_allow_html=True)
        if msg.get("steps"):
            with st.expander(f"Xem {len([s for s in msg['steps'] if s[0] != 'loop'])} bước suy luận"):
                st.markdown(render_reasoning(msg["steps"]), unsafe_allow_html=True)

# ── Input ──
typed = st.chat_input("Nhắn tin cho trợ lý…", disabled=not provider_ok)
user_text = pending or typed

if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    st.markdown(f'<div class="row row-user"><div class="bubble b-user">'
                f'{html.escape(user_text)}</div></div>', unsafe_allow_html=True)

    buffer = io.StringIO()
    with st.spinner(""):
        try:
            with contextlib.redirect_stdout(buffer):
                call_agent(user_text, provider, mcp_server)
            error = None
        except Exception as exc:  # noqa: BLE001
            error = exc

    if error:
        answer = f"Lỗi khi chạy Agent: {error}"
        steps = []
    else:
        steps, answer = parse_log(buffer.getvalue())

    st.session_state.messages.append({"role": "assistant", "content": answer, "steps": steps})
    st.rerun()
