"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import ProtectedRoute from "@/components/ProtectedRoute";
import Sidebar from "@/components/Sidebar";
import { getCurrentUser } from "@/lib/api";
import { clearToken } from "@/lib/auth";
import type { User } from "@/types/auth";
export default function DashboardPage() { const router=useRouter(); const [user,setUser]=useState<User|null>(null); useEffect(()=>{getCurrentUser().then(setUser).catch(()=>{clearToken();router.replace("/login")})},[router]); if(!user)return <ProtectedRoute><></></ProtectedRoute>; return <ProtectedRoute><main className="dashboard"><Sidebar/><section className="content"><Navbar name={user.name}/><h1 style={{marginTop:28}}>Your dashboard</h1><p className="muted">Your AI Job Copilot is ready.</p><div className="metric-grid">{[["Jobs Discovered","0"],["Strong Matches","0"],["Applications","0"],["Interviews","0"]].map(([label,value])=><div className="card" key={label}><div className="metric-label">{label}</div><div className="metric">{value}</div></div>)}</div><div className="phase-grid">{[["Resume","Upload and analyze your resume — Coming in Phase 2"],["Job Matching","Find jobs that match your profile — Coming later"],["Applications","Prepare and track applications — Coming later"]].map(([title,copy])=><div className="card phase-card" key={title}><h3>{title}</h3><p>{copy}</p></div>)}</div></section></main></ProtectedRoute> }
