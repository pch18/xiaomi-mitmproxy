"""Patch the local mitmweb install with Xiaomi plaintext detail tabs."""

from __future__ import annotations

from pathlib import Path

import mitmproxy

STYLE_LINK = '      <link rel="stylesheet" href="./static/xiaomi-comment.css">\n'
STYLE = """\
section.xiaomi-decoded {
    height: 100%;
    overflow: auto;
    padding: 1em;
}

section.xiaomi-decoded pre {
    background: transparent;
    border: 0;
    font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
    font-size: 13px;
    margin: 0;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
}

.xiaomi-json-node {
    margin-left: 1.25em;
}

.xiaomi-json-node > summary {
    cursor: pointer;
    line-height: 1.7;
    list-style-position: outside;
    user-select: text;
}

.xiaomi-json-children {
    border-left: 1px solid #ddd;
    margin-left: .15em;
    padding-left: .35em;
}

.xiaomi-json-leaf {
    line-height: 1.7;
    margin-left: 1.25em;
    user-select: text;
}

.xiaomi-json-close {
    line-height: 1.7;
    user-select: text;
}

.xiaomi-json-key {
    color: #8250df;
}

.xiaomi-json-string {
    color: #116329;
}

.xiaomi-json-value,
.xiaomi-json-punctuation {
    color: #0550ae;
}

.xiaomi-json-node[open] > summary .xiaomi-json-folded {
    display: none;
}

.nav-tabs > .xiaomi-clear-all-nav {
    background-color: #d9534f;
    border: 1px solid #d43f3a;
    border-radius: 4px;
    color: #fff;
    cursor: pointer;
    margin: 1px 6px 1px 8px;
    padding: 2px 10px;
}

.nav-tabs > .xiaomi-clear-all-nav:hover,
.nav-tabs > .xiaomi-clear-all-nav:focus {
    background-color: #c9302c;
    border-color: #ac2925;
    color: #fff;
}

"""

BACKEND_NEEDLE = "    if flow.client_conn:\n"
BACKEND_PATCH = """\
    if "xiaomi_decoded" in flow.metadata:
        f["xiaomi_decoded"] = flow.metadata["xiaomi_decoded"]

    if flow.client_conn:
"""

ORIGINAL_COMPONENT = 'const ii={request:Or,response:Mr,error:Br,connection:Ur,timing:Wr,websocket:Kr,tcpmessages:Gr,udpmessages:Yr,dnsrequest:Hr,dnsresponse:Vr,comment:zr};'
LEGACY_COMPONENT = 'function Xd(t){const{flow:e}=t;return o.jsx("section",{className:"xiaomi-decoded",children:o.jsx("pre",{children:JSON.stringify(e.xiaomi_decoded,null,2)})})}Xd.displayName="Xiaomi Decoded";const ii={request:Or,response:Mr,error:Br,connection:Ur,timing:Wr,websocket:Kr,tcpmessages:Gr,udpmessages:Yr,dnsrequest:Hr,dnsresponse:Vr,comment:zr,xiaomidecoded:Xd};'
SINGLE_COMPONENT = 'function XiaomiDecodedFlowDetailTab(t){const{flow:e}=t;return o.jsx("section",{className:"xiaomi-decoded",children:o.jsx("pre",{children:JSON.stringify(e.xiaomi_decoded,null,2)})})}XiaomiDecodedFlowDetailTab.displayName="Xiaomi Decoded";const ii={request:Or,response:Mr,error:Br,connection:Ur,timing:Wr,websocket:Kr,tcpmessages:Gr,udpmessages:Yr,dnsrequest:Hr,dnsresponse:Vr,comment:zr,xiaomidecoded:XiaomiDecodedFlowDetailTab};'
SPLIT_COMPONENTS = 'function XiaomiRequestFlowDetailTab(t){const{flow:e}=t;return o.jsx("section",{className:"xiaomi-decoded",children:o.jsx("pre",{children:JSON.stringify(e.xiaomi_decoded.request,null,2)})})}XiaomiRequestFlowDetailTab.displayName="Xiaomi Request";function XiaomiResponseFlowDetailTab(t){const{flow:e}=t;return o.jsx("section",{className:"xiaomi-decoded",children:o.jsx("pre",{children:JSON.stringify(e.xiaomi_decoded.response,null,2)})})}XiaomiResponseFlowDetailTab.displayName="Xiaomi Response";const ii={request:Or,response:Mr,error:Br,connection:Ur,timing:Wr,websocket:Kr,tcpmessages:Gr,udpmessages:Yr,dnsrequest:Hr,dnsresponse:Vr,comment:zr,xiaomirequest:XiaomiRequestFlowDetailTab,xiaomiresponse:XiaomiResponseFlowDetailTab};'
VIEWER_COMPONENTS = 'function XiaomiJsonTreeNode(t){const{label:e,value:s}=t;if(s!==null&&typeof s=="object"){const i=Array.isArray(s),r=Object.entries(s);return o.jsxs("details",{open:!0,className:"xiaomi-json-node",children:[o.jsxs("summary",{children:[e!==void 0&&o.jsx("span",{className:"xiaomi-json-key",children:e}),e!==void 0&&": ",o.jsx("span",{className:"xiaomi-json-type",children:i?`Array(${r.length})`:`Object(${r.length})`})]}),o.jsx("div",{className:"xiaomi-json-children",children:r.map(([n,l])=>o.jsx(XiaomiJsonTreeNode,{label:n,value:l},n))})]})}return o.jsxs("div",{className:"xiaomi-json-leaf",children:[o.jsx("span",{className:"xiaomi-json-key",children:e}),": ",o.jsx("span",{className:typeof s=="string"?"xiaomi-json-string":"xiaomi-json-value",children:JSON.stringify(s)})]})}function XiaomiPayloadViewer(t){const{payload:e}=t;return o.jsx("section",{className:"xiaomi-decoded",children:e.ok?o.jsx(XiaomiJsonTreeNode,{value:e.data}):o.jsxs(o.Fragment,{children:[o.jsx("div",{className:"alert alert-warning",children:e.error}),o.jsx("h4",{children:"Raw body"}),o.jsx("pre",{children:e.raw})]})})}function XiaomiRequestFlowDetailTab(t){const{flow:e}=t;return o.jsx(XiaomiPayloadViewer,{payload:e.xiaomi_decoded.request})}XiaomiRequestFlowDetailTab.displayName="Xiaomi Request";function XiaomiResponseFlowDetailTab(t){const{flow:e}=t;return o.jsx(XiaomiPayloadViewer,{payload:e.xiaomi_decoded.response})}XiaomiResponseFlowDetailTab.displayName="Xiaomi Response";const ii={request:Or,response:Mr,error:Br,connection:Ur,timing:Wr,websocket:Kr,tcpmessages:Gr,udpmessages:Yr,dnsrequest:Hr,dnsresponse:Vr,comment:zr,xiaomirequest:XiaomiRequestFlowDetailTab,xiaomiresponse:XiaomiResponseFlowDetailTab};'
TEXT_VIEWER_COMPONENTS = 'function XiaomiJsonTextNode(t){const{label:e,value:s,comma:i=!1}=t,r=e!==void 0?o.jsxs(o.Fragment,{children:[o.jsx("span",{className:"xiaomi-json-key",children:JSON.stringify(e)}),": "]}):null;if(s!==null&&typeof s=="object"){const n=Array.isArray(s),l=Object.entries(s),a=n?"[":"{",d=n?"]":"}";return o.jsxs("details",{open:!0,className:"xiaomi-json-node",children:[o.jsxs("summary",{children:[r,o.jsx("span",{className:"xiaomi-json-punctuation",children:a}),o.jsxs("span",{className:"xiaomi-json-folded",children:[" … ",d,i&&","]})]}),o.jsxs("div",{className:"xiaomi-json-children",children:[l.map(([f,p],h)=>o.jsx(XiaomiJsonTextNode,{label:n?void 0:f,value:p,comma:h<l.length-1},f)),o.jsx("div",{className:"xiaomi-json-close",children:d+(i?",":"")})]})]})}return o.jsxs("div",{className:"xiaomi-json-leaf",children:[r,o.jsx("span",{className:typeof s=="string"?"xiaomi-json-string":"xiaomi-json-value",children:JSON.stringify(s)}),i&&","]})}function XiaomiPayloadViewer(t){const{payload:e}=t;return o.jsx("section",{className:"xiaomi-decoded",children:e.ok?o.jsx(XiaomiJsonTextNode,{value:e.data}):o.jsxs(o.Fragment,{children:[o.jsx("div",{className:"alert alert-warning",children:e.error}),o.jsx("h4",{children:"Raw body"}),o.jsx("pre",{children:e.raw})]})})}function XiaomiRequestFlowDetailTab(t){const{flow:e}=t;return o.jsx(XiaomiPayloadViewer,{payload:e.xiaomi_decoded.request})}XiaomiRequestFlowDetailTab.displayName="Xiaomi Request";function XiaomiResponseFlowDetailTab(t){const{flow:e}=t;return o.jsx(XiaomiPayloadViewer,{payload:e.xiaomi_decoded.response})}XiaomiResponseFlowDetailTab.displayName="Xiaomi Response";const ii={request:Or,response:Mr,error:Br,connection:Ur,timing:Wr,websocket:Kr,tcpmessages:Gr,udpmessages:Yr,dnsrequest:Hr,dnsresponse:Vr,comment:zr,xiaomirequest:XiaomiRequestFlowDetailTab,xiaomiresponse:XiaomiResponseFlowDetailTab};'
ALIGNED_TEXT_VIEWER_COMPONENTS = 'function XiaomiJsonTextNode(t){const{label:e,value:s,comma:i=!1}=t,r=e!==void 0?o.jsxs(o.Fragment,{children:[o.jsx("span",{className:"xiaomi-json-key",children:JSON.stringify(e)}),": "]}):null;if(s!==null&&typeof s=="object"){const n=Array.isArray(s),l=Object.entries(s),a=n?"[":"{",d=n?"]":"}";return o.jsxs("details",{open:!0,className:"xiaomi-json-node",children:[o.jsxs("summary",{children:[r,o.jsx("span",{className:"xiaomi-json-punctuation",children:a}),o.jsxs("span",{className:"xiaomi-json-folded",children:[" … ",d,i&&","]})]}),o.jsx("div",{className:"xiaomi-json-children",children:l.map(([f,p],h)=>o.jsx(XiaomiJsonTextNode,{label:n?void 0:f,value:p,comma:h<l.length-1},f))}),o.jsx("div",{className:"xiaomi-json-close",children:d+(i?",":"")})]})}return o.jsxs("div",{className:"xiaomi-json-leaf",children:[r,o.jsx("span",{className:typeof s=="string"?"xiaomi-json-string":"xiaomi-json-value",children:JSON.stringify(s)}),i&&","]})}function XiaomiPayloadViewer(t){const{payload:e}=t;return o.jsx("section",{className:"xiaomi-decoded",children:e.ok?o.jsx(XiaomiJsonTextNode,{value:e.data}):o.jsxs(o.Fragment,{children:[o.jsx("div",{className:"alert alert-warning",children:e.error}),o.jsx("h4",{children:"Raw body"}),o.jsx("pre",{children:e.raw})]})})}function XiaomiRequestFlowDetailTab(t){const{flow:e}=t;return o.jsx(XiaomiPayloadViewer,{payload:e.xiaomi_decoded.request})}XiaomiRequestFlowDetailTab.displayName="Xiaomi Request";function XiaomiResponseFlowDetailTab(t){const{flow:e}=t;return o.jsx(XiaomiPayloadViewer,{payload:e.xiaomi_decoded.response})}XiaomiResponseFlowDetailTab.displayName="Xiaomi Response";const ii={request:Or,response:Mr,error:Br,connection:Ur,timing:Wr,websocket:Kr,tcpmessages:Gr,udpmessages:Yr,dnsrequest:Hr,dnsresponse:Vr,comment:zr,xiaomirequest:XiaomiRequestFlowDetailTab,xiaomiresponse:XiaomiResponseFlowDetailTab};'

ORIGINAL_TABS = 'return t.error&&e.push("error"),e.push("connection"),e.push("timing"),e.push("comment"),e}'
SINGLE_TAB = 'return t.error&&e.push("error"),t.xiaomi_decoded&&e.push("xiaomidecoded"),e.push("connection"),e.push("timing"),e.push("comment"),e}'
SPLIT_TABS = 'return t.error&&e.push("error"),t.xiaomi_decoded?.request!==void 0&&e.push("xiaomirequest"),t.xiaomi_decoded?.response!==void 0&&e.push("xiaomiresponse"),e.push("connection"),e.push("timing"),e.push("comment"),e}'
ALWAYS_TABS = 'return t.error&&e.push("error"),t.xiaomi_decoded&&e.push("xiaomirequest"),t.xiaomi_decoded&&e.push("xiaomiresponse"),e.push("connection"),e.push("timing"),e.push("comment"),e}'
EMPTY_SEARCH = 'const Ti={search:"",highlight:""}'
DEFAULT_SEARCH = 'const Ti={search:"mi.com",highlight:""}'
CONFIRM_CLEAR = 'p=()=>confirm("Delete all flows?")&&s(Oi())'
DIRECT_CLEAR = 'p=()=>s(Oi())'
ORIGINAL_FLOW_TOOLBAR = 'function Su(){const t=k.c(2),e=G();let s;return t[0]!==e?(s=o.jsx(pe,{className:"btn-sm",title:"[a]ccept all",icon:"fa-forward text-success",onClick:()=>e(Di()),children:"Resume All"}),t[0]=e,t[1]=s):s=t[1],s}function Vs(t)'
QUICK_CLEAR_FLOW_TOOLBAR = 'function Su(){const t=k.c(2),e=G();let s;return t[0]!==e?(s=o.jsx(pe,{className:"btn-sm",title:"[a]ccept all",icon:"fa-forward text-success",onClick:()=>e(Di()),children:"Resume All"}),t[0]=e,t[1]=s):s=t[1],s}function XiaomiClearAllToolbarButton(){const t=k.c(2),e=G();let s;return t[0]!==e?(s=o.jsx(pe,{className:"btn-sm btn-danger",title:"Clear all flows without confirmation",icon:"fa-trash",onClick:()=>e(Oi()),children:"Clear All"}),t[0]=e,t[1]=s):s=t[1],s}function Vs(t)'
ORIGINAL_INTERCEPT_TOOLBAR = 'o.jsxs("div",{className:"menu-content",children:[o.jsx(xu,{}),o.jsx(Su,{})]})'
QUICK_CLEAR_INTERCEPT_TOOLBAR = 'o.jsxs("div",{className:"menu-content",children:[o.jsx(xu,{}),o.jsx(Su,{}),o.jsx(XiaomiClearAllToolbarButton,{})]})'
ORIGINAL_MAIN_NAV = 'let j;t[18]===Symbol.for("react.memo_cache_sentinel")?(j=o.jsx(gt,{children:o.jsx(mu,{})}),t[18]=j):j=t[18];let y;t[19]!==_?(y=o.jsxs("nav",{className:"nav-tabs nav-tabs-lg",children:[g,_,j]}),t[19]=_,t[20]=y):y=t[20];'
QUICK_CLEAR_MAIN_NAV = 'let j;t[18]===Symbol.for("react.memo_cache_sentinel")?(j=o.jsx(gt,{children:o.jsx(mu,{})}),t[18]=j):j=t[18];let y;t[19]!==_?(y=o.jsxs("nav",{className:"nav-tabs nav-tabs-lg",children:[g,_,o.jsx(XiaomiClearAllNavButton,{}),j]}),t[19]=_,t[20]=y):y=t[20];'
OLD_CLEAR_ALL_NAV_BUTTON = '}function XiaomiClearAllNavButton(){const t=k.c(2),e=G();let s;return t[0]!==e?(s=o.jsxs("a",{href:"#",className:"xiaomi-clear-all-nav",title:"Clear all flows without confirmation",onClick:i=>{i.preventDefault(),e(Oi())},children:[o.jsx("i",{className:"fa fa-fw fa-trash"})," Clear All"]}),t[0]=e,t[1]=s):s=t[1],s}function Vs(t)'
SOLID_CLEAR_ALL_NAV_BUTTON = '}function XiaomiClearAllNavButton(){const t=k.c(2),e=G();let s;return t[0]!==e?(s=o.jsxs("button",{type:"button",className:"xiaomi-clear-all-nav",title:"Clear all flows without confirmation",onClick:()=>e(Oi()),children:[o.jsx("i",{className:"fa fa-fw fa-trash"})," Clear All"]}),t[0]=e,t[1]=s):s=t[1],s}function Vs(t)'
QUICK_CLEAR_FLOW_TOOLBAR_WITH_NAV_BUTTON = QUICK_CLEAR_FLOW_TOOLBAR.replace(
    "}function Vs(t)",
    SOLID_CLEAR_ALL_NAV_BUTTON,
)
DYNAMIC_FLOW_TAB = 'l=[xe.Capture,xe.FlowList,xe.Options],i.length>0&&l.push(xe.Flow)'
FIXED_FLOW_TAB = 'l=[xe.Capture,xe.FlowList,xe.Options,xe.Flow]'
CLICKABLE_FLOW_TAB_MAP = '_=l.map(N=>o.jsx("a",{href:"#",className:je({active:N===s}),onClick:E=>p(N,E),children:li[N].title},N))'
DISABLED_EMPTY_FLOW_TAB_MAP = '_=l.map(N=>{const E=N===xe.Flow&&i.length===0;return o.jsx("a",{href:"#",className:je({active:N===s,disabled:E}),onClick:T=>{E?T.preventDefault():p(N,T)},children:li[N].title},N)})'


def _patch_backend(path: Path) -> None:
    text = path.read_text()
    if 'f["xiaomi_decoded"]' not in text:
        if BACKEND_NEEDLE not in text:
            raise RuntimeError(f"backend patch target not found in {path}")
        path.write_text(text.replace(BACKEND_NEEDLE, BACKEND_PATCH, 1))


def _patch_frontend(path: Path) -> None:
    text = path.read_text()
    if LEGACY_COMPONENT in text:
        text = text.replace(LEGACY_COMPONENT, ALIGNED_TEXT_VIEWER_COMPONENTS, 1)
    elif SINGLE_COMPONENT in text:
        text = text.replace(SINGLE_COMPONENT, ALIGNED_TEXT_VIEWER_COMPONENTS, 1)
    elif SPLIT_COMPONENTS in text:
        text = text.replace(SPLIT_COMPONENTS, ALIGNED_TEXT_VIEWER_COMPONENTS, 1)
    elif VIEWER_COMPONENTS in text:
        text = text.replace(VIEWER_COMPONENTS, ALIGNED_TEXT_VIEWER_COMPONENTS, 1)
    elif TEXT_VIEWER_COMPONENTS in text:
        text = text.replace(TEXT_VIEWER_COMPONENTS, ALIGNED_TEXT_VIEWER_COMPONENTS, 1)
    elif ALIGNED_TEXT_VIEWER_COMPONENTS not in text:
        if ORIGINAL_COMPONENT not in text:
            raise RuntimeError(f"frontend component patch target not found in {path}")
        text = text.replace(ORIGINAL_COMPONENT, ALIGNED_TEXT_VIEWER_COMPONENTS, 1)

    if SINGLE_TAB in text:
        text = text.replace(SINGLE_TAB, ALWAYS_TABS, 1)
    elif SPLIT_TABS in text:
        text = text.replace(SPLIT_TABS, ALWAYS_TABS, 1)
    elif ALWAYS_TABS not in text:
        if ORIGINAL_TABS not in text:
            raise RuntimeError(f"frontend tabs patch target not found in {path}")
        text = text.replace(ORIGINAL_TABS, ALWAYS_TABS, 1)

    if DEFAULT_SEARCH not in text:
        if EMPTY_SEARCH not in text:
            raise RuntimeError(f"frontend search patch target not found in {path}")
        text = text.replace(EMPTY_SEARCH, DEFAULT_SEARCH, 1)

    if CONFIRM_CLEAR in text:
        text = text.replace(CONFIRM_CLEAR, DIRECT_CLEAR, 1)

    if OLD_CLEAR_ALL_NAV_BUTTON in text:
        text = text.replace(OLD_CLEAR_ALL_NAV_BUTTON, SOLID_CLEAR_ALL_NAV_BUTTON, 1)

    if QUICK_CLEAR_FLOW_TOOLBAR_WITH_NAV_BUTTON not in text:
        if QUICK_CLEAR_FLOW_TOOLBAR in text:
            text = text.replace(QUICK_CLEAR_FLOW_TOOLBAR, QUICK_CLEAR_FLOW_TOOLBAR_WITH_NAV_BUTTON, 1)
        elif ORIGINAL_FLOW_TOOLBAR in text:
            text = text.replace(ORIGINAL_FLOW_TOOLBAR, QUICK_CLEAR_FLOW_TOOLBAR_WITH_NAV_BUTTON, 1)
        else:
            raise RuntimeError(f"frontend clear button patch target not found in {path}")

    if QUICK_CLEAR_INTERCEPT_TOOLBAR in text:
        text = text.replace(QUICK_CLEAR_INTERCEPT_TOOLBAR, ORIGINAL_INTERCEPT_TOOLBAR, 1)

    if QUICK_CLEAR_MAIN_NAV not in text:
        if ORIGINAL_MAIN_NAV not in text:
            raise RuntimeError(f"frontend main navigation patch target not found in {path}")
        text = text.replace(ORIGINAL_MAIN_NAV, QUICK_CLEAR_MAIN_NAV, 1)

    if FIXED_FLOW_TAB in text:
        text = text.replace(FIXED_FLOW_TAB, DYNAMIC_FLOW_TAB, 1)

    if DISABLED_EMPTY_FLOW_TAB_MAP in text:
        text = text.replace(DISABLED_EMPTY_FLOW_TAB_MAP, CLICKABLE_FLOW_TAB_MAP, 1)

    if QUICK_CLEAR_FLOW_TOOLBAR_WITH_NAV_BUTTON not in text:
        if ORIGINAL_FLOW_TOOLBAR not in text:
            raise RuntimeError(f"frontend clear button patch target not found in {path}")
        text = text.replace(ORIGINAL_FLOW_TOOLBAR, QUICK_CLEAR_FLOW_TOOLBAR_WITH_NAV_BUTTON, 1)
    path.write_text(text)


def main() -> None:
    package_dir = Path(mitmproxy.__file__).parent
    web_dir = package_dir / "tools" / "web"
    index_path = web_dir / "index.html"
    style_path = web_dir / "static" / "xiaomi-comment.css"

    html = index_path.read_text()
    if STYLE_LINK not in html:
        index_path.write_text(html.replace("    </head>\n", f"{STYLE_LINK}    </head>\n"))
    style_path.write_text(STYLE)
    _patch_backend(web_dir / "app.py")
    _patch_frontend(next((web_dir / "static").glob("index-*.js")))
    print(f"patched {web_dir}")


if __name__ == "__main__":
    main()
