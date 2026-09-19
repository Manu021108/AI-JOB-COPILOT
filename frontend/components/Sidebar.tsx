"use client";
import { usePathname } from "next/navigation";

export default function Sidebar() {
  const pathname = usePathname();
  const nav = ["Dashboard", "Resume", "Jobs", "Applications", "Analytics", "Settings"];
  const hrefs = ["/dashboard", "/resume", "#", "#", "#", "#"];
  return (
    <aside className="side">
      <div className="brand">AI Job Copilot</div>
      {nav.map((item, index) => {
        const active = pathname.startsWith(hrefs[index]);
        return (
          <a className={active ? "active" : ""} href={hrefs[index]} key={item}>
            {item}
            {index > 1 && <span className="soon">SOON</span>}
          </a>
        );
      })}
    </aside>
  );
}