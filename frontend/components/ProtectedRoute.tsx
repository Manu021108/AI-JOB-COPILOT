"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";
export default function ProtectedRoute({children}:{children:React.ReactNode}) { const router=useRouter(); const [ready,setReady]=useState(false); useEffect(()=>{if(!getToken()) router.replace("/login"); else setReady(true)},[router]); return ready ? <>{children}</> : null; }
