"use client";
import { useRouter } from "next/navigation";
import { clearToken } from "@/lib/auth";
export default function Navbar({ name }: {name: string}) { const router=useRouter(); return <div className="topbar"><div><strong>Welcome, {name}</strong><div className="muted">Your application workspace</div></div><button className="logout" onClick={() => {clearToken();router.replace("/login")}}>Logout</button></div> }
