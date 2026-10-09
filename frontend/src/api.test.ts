import {describe,it,expect} from 'vitest';
import {metric} from './api';
import {useLive,useUI} from './stores';
describe('truthful metric rendering',()=>{it('distinguishes absent sensors from zero measurements',()=>{expect(metric(null,'%')).toBe('—');expect(metric(undefined)).toBe('—');expect(metric(0,'%')).toBe('0.0%')})});
describe('isolated state',()=>{it('changing view preferences does not alter the recorded analysis',()=>{const packet={state:{status:'paused',seq:13,tracks:[],events:[]},image:null};useLive.getState().setPacket(packet);useUI.getState().setTab('replay');useUI.getState().toggleOverlay();expect(useLive.getState().packet).toBe(packet);expect(useLive.getState().packet.state.seq).toBe(13)})});
