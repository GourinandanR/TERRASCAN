import {useEffect,useState} from "react";
const IDLE_LIMIT_MS=30*60*1000;
export function useSessionLifecycle(token:string|null,onExpire:()=>void){
 const [lastActivity,setLastActivity]=useState(()=>Date.now());
 useEffect(()=>{
  if(!token)return;
  const touch=()=>setLastActivity(Date.now());
  const events:(keyof WindowEventMap)[]=["pointerdown","keydown","touchstart","mousemove"];
  events.forEach(name=>window.addEventListener(name,touch,{passive:true}));
  const timer=window.setInterval(()=>{
   if(Date.now()-lastActivity>=IDLE_LIMIT_MS)onExpire();
  },15_000);
  return ()=>{events.forEach(name=>window.removeEventListener(name,touch));window.clearInterval(timer);};
 },[token,lastActivity,onExpire]);
}
