const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const M = require('../model.js');
const ctx = {}; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../data.js'),'utf8')+';globalThis.seed=companies;',ctx);
const initial = () => M.initial(ctx.seed);
const storage = () => {const data=new Map();return {getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k)};};
const offerValues = {orgId:'1',title:'Découverte du numérique',description:'Un stage de découverte.',start:'2099-06-01',end:'2099-06-15',capacity:1,status:'published'};

test('seed preserves all original organizations and creates separate offers',()=>{
 const s=initial();assert.equal(s.orgs.length,ctx.seed.length);assert.equal(s.offers.length,ctx.seed.length);assert.ok(M.valid(s));
 assert.equal(s.orgs[0].name,ctx.seed[0].name);assert.ok(s.orgs.every(o=>!o.owner));
 assert.ok(s.orgs.every(o=>Number.isFinite(o.latitude)&&Number.isFinite(o.longitude)));
});
test('favorites persist and toggle without duplicates',()=>{
 const db=storage();let s=M.transact(initial(),db,'favorite',{id:'offer-1'});
 assert.equal(M.load(db,ctx.seed).favorites.length,1);
 s=M.transact(s,db,'favorite',{id:'offer-1'});assert.equal(s.favorites.length,0);
});
test('failed storage writes leave state untouched',()=>{
 const s=initial(),before=JSON.stringify(s);
 assert.throws(()=>M.transact(s,{setItem(){throw Error('quota');}},'favorite',{id:'offer-1'}),/quota/);
 assert.equal(JSON.stringify(s),before);
});
test('corrupt storage is not silently overwritten',()=>{
 const db=storage();db.setItem(M.KEY,'invalid');assert.throws(()=>M.load(db,ctx.seed));assert.equal(db.getItem(M.KEY),'invalid');
});
test('claim approval assigns ownership; duplicate requests are rejected',()=>{
 const s=initial();M.apply(s,'switch',{id:'representative'});
 M.apply(s,'claim',{id:'1',reason:'Je représente cette organisation de démonstration.'});
 assert.throws(()=>M.apply(s,'claim',{id:'1',reason:'Une autre demande.'}),/déjà/);
 assert.equal(M.manage(s,s.orgs[0]),false);
 M.apply(s,'switch',{id:'admin'});M.apply(s,'claim-review',{id:s.claims[0].id,status:'approved'});
 M.apply(s,'switch',{id:'representative'});assert.ok(M.manage(s,s.orgs[0]));assert.equal(M.manage(s,s.orgs[1]),false);
 M.apply(s,'offer-save',offerValues);assert.equal(s.offers.at(-1).orgId,'1');
 assert.throws(()=>M.apply(s,'offer-save',{...offerValues,orgId:'2'}),/appartient/);
});
test('new organizations need approval before publishing',()=>{
 const s=initial();M.apply(s,'switch',{id:'representative'});
 const v={name:'Entreprise locale test',address:'12 rue exemple',sector:'IT',description:'Organisation de démonstration'};
 M.apply(s,'org-save',v);const o=s.orgs.at(-1);assert.equal(o.status,'pending');
 assert.throws(()=>M.apply(s,'org-save',v),/existe déjà/);
 assert.throws(()=>M.apply(s,'offer-save',{...offerValues,orgId:o.id}),/approuvée/);
 M.apply(s,'offer-save',{...offerValues,orgId:o.id,status:'draft'});assert.equal(s.offers.at(-1).status,'draft');
 M.apply(s,'switch',{id:'admin'});M.apply(s,'org-status',{id:o.id,status:'approved'});
 M.apply(s,'switch',{id:'representative'});M.apply(s,'offer-save',{...offerValues,orgId:o.id});
 assert.equal(s.offers.at(-1).status,'published');
});
test('invalid periods, impossible dates and capacities are rejected',()=>{
 const s=initial();M.apply(s,'switch',{id:'admin'});
 for(const v of [{end:'2099-05-01'},{start:'2099-02-30'},{capacity:0},{capacity:1.5},{capacity:101},{start:''},{end:'2000-01-01',start:'1999-01-01'}])
  assert.throws(()=>M.apply(s,'offer-save',{...offerValues,...v}));
});
test('applications respect capacity, duplicates and withdrawal',()=>{
 const s=initial();M.apply(s,'apply',{id:'offer-1',message:'Je souhaite découvrir ce métier.'});
 assert.throws(()=>M.apply(s,'apply',{id:'offer-1',message:'Nouvelle demande.'}),/déjà/);
 const a=s.applications[0];M.apply(s,'switch',{id:'admin'});M.apply(s,'application-status',{id:a.id,status:'accepted'});
 assert.equal(M.remaining(s,s.offers[0]),0);assert.equal(M.available(s,s.offers[0]),false);
 M.apply(s,'switch',{id:'student'});M.apply(s,'application-status',{id:a.id,status:'withdrawn'});
 assert.equal(M.remaining(s,s.offers[0]),1);M.apply(s,'apply',{id:'offer-1',message:'Une candidature après retrait.'});
 assert.equal(s.applications.length,2);
});
test('students cannot modify organizations or process ownership requests',()=>{
 const s=initial();assert.throws(()=>M.apply(s,'org-status',{id:'1',status:'approved'}));
 assert.throws(()=>M.apply(s,'org-save',{id:'1',name:'Changed'}));assert.throws(()=>M.apply(s,'offer-save',offerValues));
});
test('archived offers and blocked organizations cannot receive applications',()=>{
 const s=initial();M.apply(s,'switch',{id:'admin'});M.apply(s,'offer-status',{id:'offer-1',status:'archived'});
 M.apply(s,'org-status',{id:'2',status:'blocked'});M.apply(s,'switch',{id:'student'});
 assert.throws(()=>M.apply(s,'apply',{id:'offer-1',message:'Une candidature test.'}));
 assert.throws(()=>M.apply(s,'apply',{id:'offer-2',message:'Une candidature test.'}));
});
test('capacity cannot drop below accepted applications',()=>{
 const s=initial();M.apply(s,'switch',{id:'admin'});M.apply(s,'offer-save',{...offerValues,id:'offer-1',capacity:2});
 s.applications.push({id:'a',offerId:'offer-1',userId:'student',status:'accepted'},{id:'b',offerId:'offer-1',userId:'other',status:'accepted'});
 assert.throws(()=>M.apply(s,'offer-save',{...offerValues,id:'offer-1'}),/inférieur/);
});
test('search normalization handles accents and whitespace',()=>assert.equal(M.normalize('  Médecine  '),'medecine'));
