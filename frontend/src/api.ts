export async function api<T=any>(path:string,options:RequestInit={}):Promise<T>{
 const response=await fetch('/api'+path,{...options,headers:options.body instanceof FormData?options.headers:{'Content-Type':'application/json',...options.headers}});
 if(!response.ok){let message='Request failed';try{const data=await response.json();message=typeof data.detail==='string'?data.detail:JSON.stringify(data.detail)}catch{message=response.statusText}throw new Error(message)}
 return response.json();
}
export const post=(path:string,body:unknown)=>api(path,{method:'POST',body:JSON.stringify(body)});
export function download(path:string){const a=document.createElement('a');a.href='/api'+path;a.download='';a.click()}
export const clock=(value?:number)=>value?new Date(value*1000).toLocaleTimeString([], {hour12:false}):'—';
export const metric=(value:number|null|undefined,unit='')=>value==null?'—':`${value.toFixed(value<10?1:0)}${unit}`;
