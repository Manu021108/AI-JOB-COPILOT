"use client";
import { usePathname } from "next/navigation";

export default function Sidebar() {
  const pathname = usePathname();
  const nav = ["Dashboard", "Resume", "Jobs", "Applications", "Analytics", "Settings"];
  const hrefs = ["/dashboard", "/resume", "/jobs", "#", "#", "#"];
  return (
    <aside className="side">
      <div className="brand">AI Job Copilot</div>
      {nav.map((item, index) => {
        const active = hrefs[index] !== "#" && pathname.startsWith(hrefs[index]);
        return (
          <a className={active ? "active" : ""} href={hrefs[index]} key={item}>
            {item}
            {hrefs[index] === "#" && <span className="soon">SOON</span>}
          </a>
        );
      })}
    </aside>
  );
}