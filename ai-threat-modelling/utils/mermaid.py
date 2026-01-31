import streamlit.components.v1 as components


def render_mermaid(mermaid_code: str, height: int = 650):
    """
    Renders Mermaid diagrams inside Streamlit using Mermaid.js
    """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    </head>
    <body>
        <div class="mermaid">
{mermaid_code}
        </div>

        <script>
            mermaid.initialize({{
                startOnLoad: true,
                theme: "default",
                securityLevel: "loose"
            }});
        </script>
    </body>
    </html>
    """

    components.html(html, height=height, scrolling=True)
