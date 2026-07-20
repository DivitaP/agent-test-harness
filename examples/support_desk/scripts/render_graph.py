"""Render the Support Desk graph, retaining Mermaid text if PNG rendering fails."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent))

from support_desk.graph import build_app


def main() -> None:
    graph = build_app(render_only=True).get_graph()
    mermaid = graph.draw_mermaid()
    print(mermaid)
    output_dir = Path(__file__).resolve().parents[1] / "docs"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "support_graph.mmd").write_text(mermaid, encoding="utf-8")
    try:
        graph.draw_mermaid_png(output_file_path=str(output_dir / "support_graph.png"))
        print(f"wrote {output_dir / 'support_graph.png'}")
    except Exception as exc:
        print(f"png render skipped ({exc}); wrote {output_dir / 'support_graph.mmd'}")


if __name__ == "__main__":
    main()
