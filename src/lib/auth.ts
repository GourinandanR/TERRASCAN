const API_BASE=(import.meta.env.VITE_API_BASE_URL||import.meta.env.VITE_API_URL||"http://127.0.0.1:8000").replace(/\/$/,"");
export type TerrascanRole="viewer"|"analyst"|"admin";
export interface TerrascanUser{id:number;username:string;role:TerrascanRole}
export async function login(username:string,password:string){
 const r=await fetch(`${API_BASE}/api/auth/login`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username,password})});
 if(!r.ok)throw new Error((await r.json()).detail||"Login failed");return r.json();
}
export async function logout(token:string){
 await fetch(`${API_BASE}/api/auth/logout`,{method:"POST",headers:{Authorization:`Bearer ${token}`}});
}
