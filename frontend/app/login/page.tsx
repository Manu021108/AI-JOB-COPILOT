"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { loginUser } from "@/lib/api";
import { setToken } from "@/lib/auth";
type Form = {email:string;password:string};
export default function LoginPage() { const router=useRouter(); const {register,handleSubmit,formState:{errors,isSubmitting},setError}=useForm<Form>(); const submit=async(data:Form)=>{try{const result=await loginUser(data);setToken(result.access_token);router.replace("/dashboard")}catch(error){setError("root",{message:error instanceof Error?error.message:"Unable to sign in."})}}; return <main className="auth"><form className="form-card" onSubmit={handleSubmit(submit)}><div className="brand">AI Job Copilot</div><h1>Welcome back</h1><p className="muted">Sign in to your workspace.</p><label className="field">Email<input type="email" autoComplete="email" {...register("email",{required:"Email is required."})}/>{errors.email&&<span className="error">{errors.email.message}</span>}</label><label className="field">Password<input type="password" autoComplete="current-password" {...register("password",{required:"Password is required."})}/>{errors.password&&<span className="error">{errors.password.message}</span>}</label>{errors.root&&<p className="error">{errors.root.message}</p>}<button className="btn" style={{width:"100%",marginTop:24}} disabled={isSubmitting}>{isSubmitting?"Signing in…":"Login"}</button><p className="muted">New here? <Link href="/register" style={{color:"#3349b8"}}>Create an account</Link></p></form></main> }
