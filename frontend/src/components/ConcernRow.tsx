import { Link } from "react-router-dom";
import { Badge } from "./Widgets";
import type { Concern } from "../types";

export function ConcernRow({ concern }: { concern: Concern }) {
  const itemLinks = (concern.links ?? []).filter((l) => l.kind !== "section");
  const sectionLink = (concern.links ?? []).find((l) => l.kind === "section");
  return (
    <div className="concern">
      <div>
        <Badge tone={concern.severity}>{concern.severity}</Badge>
      </div>
      <div>
        <h4>{concern.title}</h4>
        <p>{concern.detail}</p>
        <p className="rec">{concern.recommendation}</p>
        {concern.links && concern.links.length > 0 ? (
          <div className="concern-links">
            {sectionLink ? (
              <Link className="concern-link section" to={sectionLink.href}>
                {sectionLink.label}
              </Link>
            ) : null}
            {itemLinks.map((link) => (
              <Link key={`${link.href}-${link.value}`} className="concern-link" to={link.href} title={link.meta ?? link.label}>
                <span className="mono">{link.label}</span>
                {link.meta ? <span className="meta">{link.meta}</span> : null}
              </Link>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
