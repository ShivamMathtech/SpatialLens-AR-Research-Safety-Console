import { create } from 'zustand';
import type { Packet,Settings } from '../types';
export const useLive=create<{packet:Packet;connected:boolean;setPacket:(p:Packet)=>void;setConnected:(c:boolean)=>void}>(set=>({packet:{state:{status:'idle',tracks:[],events:[]},image:null},connected:false,setPacket:packet=>set({packet}),setConnected:connected=>set({connected})}));
export const useUI=create<{tab:string;overlay:boolean;selected:string|null;setTab:(v:string)=>void;toggleOverlay:()=>void;select:(id:string|null)=>void}>(set=>({tab:'console',overlay:true,selected:null,setTab:tab=>set({tab}),toggleOverlay:()=>set(s=>({overlay:!s.overlay})),select:selected=>set({selected})}));
export const useConfig=create<{settings:Settings|null;setSettings:(s:Settings)=>void}>(set=>({settings:null,setSettings:settings=>set({settings})}));
