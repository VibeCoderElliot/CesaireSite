'use strict';

// Device-local prototype. Roles organize workflows, not a security boundary.
const CesaireModel = (() => {
  const KEY = 'cesaire_stages_v2';
  const copy = value => JSON.parse(JSON.stringify(value));
  const uid = () => globalThis.crypto?.randomUUID?.() || `id-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const clean = (value, max = 1000) => String(value || '').trim().slice(0, max);
  const normalize = value => clean(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const date = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };
  function initial(companies) {
    return {version:2, current:'student', profiles:[
      {id:'student', name:'Élève exemple', role:'student', classroom:'', interests:''},
      {id:'representative', name:'Représentant exemple', role:'representative'},
      {id:'admin', name:'Administration locale', role:'admin'}
    ], orgs:companies.map(c => ({id:String(c.id),name:c.name,sector:c.sector,metro:c.metro,address:c.address,description:c.description,email:c.email,phone:c.phone,latitude:c.latitude,longitude:c.longitude,source:c.source,status:'approved',owner:null,sample:true,featured:!!c.isFeatured})),
    offers:companies.map(c => ({id:`offer-${c.id}`,orgId:String(c.id),title:`Stage découverte · ${c.sector}`,description:c.description,tasks:c.tasks.join('\n'),requirements:c.requirements.join('\n'),duration:c.duration,schedule:c.schedule,start:'',end:'',capacity:1,status:'published',created:new Date().toISOString(),sample:true})),
    claims:[],applications:[],favorites:[],log:[]};
  }
  function valid(s) {
    return s && s.version === 2 && ['profiles','orgs','offers','claims','applications','favorites','log'].every(k=>Array.isArray(s[k])) &&
      s.profiles.some(p=>p.id===s.current) && s.profiles.every(p=>typeof p.id==='string' && ['admin','student','representative'].includes(p.role)) &&
      s.orgs.every(o=>typeof o.id==='string' && typeof o.name==='string') &&
      s.offers.every(o=>typeof o.id==='string' && typeof o.orgId==='string' && s.orgs.some(g=>g.id===o.orgId));
  }
  function load(storage, seed) {
    const raw=storage.getItem(KEY);
    if (!raw) return initial(seed);
    const s=JSON.parse(raw);
    if(!valid(s)) throw new Error('Les données locales sont incompatibles. Elles ne sont pas écrasées.');
    return s;
  }
  const actor = s => s.profiles.find(p=>p.id===s.current);
  const manage = (s,org) => !!org && (actor(s).role==='admin' || org.owner===s.current);
  const remaining = (s,offer) => offer.capacity - s.applications.filter(a=>a.offerId===offer.id && a.status==='accepted').length;
  const available = (s,o) => o.status==='published' && s.orgs.some(g=>g.id===o.orgId && g.status==='approved') && (!o.end || o.end>=date()) && remaining(s,o)>0;
  function requireThat(condition, message) { if(!condition) throw new Error(message); }
  function org(s,id) { const o=s.orgs.find(x=>x.id===id); requireThat(o,'Organisation introuvable.'); return o; }
  function offer(s,id) { const o=s.offers.find(x=>x.id===id); requireThat(o,'Stage introuvable.'); return o; }
  function apply(s, action, data = {}) {
    const p=actor(s); requireThat(p,'Profil introuvable.');
    if(action==='switch') {requireThat(s.profiles.some(x=>x.id===data.id),'Profil introuvable.'); s.current=data.id; return;}
    if(action==='profile') {p.name=clean(data.name,100)||p.name;p.classroom=clean(data.classroom,60);p.interests=clean(data.interests,500);return;}
    if(action==='favorite') {
      requireThat(p.role==='student','Choisissez un profil élève.'); offer(s,data.id);
      const i=s.favorites.findIndex(f=>f.userId===p.id && f.offerId===data.id);
      if(i>=0)s.favorites.splice(i,1);else s.favorites.push({userId:p.id,offerId:data.id});return;
    }
    if(action==='org-save') {
      requireThat(p.role!=='student','Choisissez un profil organisation ou administration.');
      let o=data.id?org(s,data.id):null;
      requireThat(!o||manage(s,o),'Cette organisation ne vous appartient pas.');
      const values={name:clean(data.name,120),sector:clean(data.sector,80),metro:clean(data.metro,100),address:clean(data.address,200),description:clean(data.description,1000),email:clean(data.email,120),phone:clean(data.phone,40)};
      requireThat(values.name.length>=2 && values.sector && values.address && values.description,'Complétez le nom, le secteur, l’adresse et la description.');
      requireThat(!values.email || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email),'Adresse email invalide.');
      requireThat(!s.orgs.some(x=>x.id!==o?.id && normalize(x.name)===normalize(values.name) && normalize(x.address)===normalize(values.address)),'Cette organisation existe déjà. Demandez à la gérer.');
      if(o)Object.assign(o,values);else{s.orgs.push({...values,id:uid(),status:p.role==='admin'?'approved':'pending',owner:p.role==='admin'?null:p.id,sample:false,featured:false});}
    } else if(action==='org-status') {
      requireThat(p.role==='admin','Action réservée à l’administration locale.');
      requireThat(['approved','rejected','blocked'].includes(data.status),'Statut invalide.');org(s,data.id).status=data.status;
    } else if(action==='claim') {
      requireThat(p.role==='representative','Choisissez un profil organisation.'); const o=org(s,data.id);
      requireThat(o.status==='approved' && !o.owner,'Cette organisation ne peut pas être revendiquée.');
      requireThat(!s.claims.some(c=>c.orgId===o.id&&c.userId===p.id&&c.status==='pending'),'Une demande est déjà en cours.');
      requireThat(clean(data.reason).length>=10,'Précisez votre lien avec l’organisation (10 caractères minimum).');
      s.claims.push({id:uid(),orgId:o.id,userId:p.id,reason:clean(data.reason),status:'pending',created:new Date().toISOString()});
    } else if(action==='claim-review') {
      requireThat(p.role==='admin','Action réservée à l’administration locale.'); const c=s.claims.find(x=>x.id===data.id);
      requireThat(c&&c.status==='pending','Demande déjà traitée ou introuvable.');
      requireThat(['approved','rejected'].includes(data.status),'Décision invalide.');const o=org(s,c.orgId);
      if(data.status==='approved') {requireThat(!o.owner&&o.status==='approved','Organisation indisponible.');o.owner=c.userId;s.claims.filter(x=>x.orgId===o.id&&x.id!==c.id&&x.status==='pending').forEach(x=>x.status='rejected');}
      c.status=data.status;
    } else if(action==='offer-save') {
      const o=org(s,data.orgId);requireThat(manage(s,o),'Cette organisation ne vous appartient pas.');
      const old=data.id?offer(s,data.id):null;requireThat(!old||old.orgId===o.id,'Organisation incompatible.');
      const v={title:clean(data.title,140),description:clean(data.description,1500),tasks:clean(data.tasks,1500),requirements:clean(data.requirements,1000),duration:clean(data.duration,80),schedule:clean(data.schedule,120),start:clean(data.start,10),end:clean(data.end,10),capacity:Number(data.capacity),status:data.status};
      requireThat(v.title.length>=3 && v.description,'Précisez le titre et la description.');
      requireThat(['draft','published','paused','archived'].includes(v.status),'Statut invalide.');
      requireThat(Number.isInteger(v.capacity)&&v.capacity>=1&&v.capacity<=100,'Le nombre de places doit être compris entre 1 et 100.');
      const validDate=x=>/^\d{4}-\d{2}-\d{2}$/.test(x)&&!Number.isNaN(Date.parse(x))&&new Date(x).toISOString().slice(0,10)===x;
      requireThat(validDate(v.start)&&validDate(v.end)&&v.end>=v.start,'Choisissez une période valide : la fin doit suivre le début.');
      requireThat(v.status!=='published'||(o.status==='approved'&&v.end>=date()),'Pour publier, l’organisation doit être approuvée et la période non terminée.');
      const accepted=old?s.applications.filter(a=>a.offerId===old.id&&a.status==='accepted').length:0;
      requireThat(v.capacity>=accepted,'Le nombre de places ne peut pas être inférieur aux candidatures acceptées.');
      if(old)Object.assign(old,v);else s.offers.push({...v,id:uid(),orgId:o.id,created:new Date().toISOString(),sample:false});
    } else if(action==='offer-status') {
      const v=offer(s,data.id),o=org(s,v.orgId);requireThat(manage(s,o),'Accès refusé.');
      requireThat(['paused','archived'].includes(data.status),'Statut invalide.');v.status=data.status;
    } else if(action==='apply') {
      requireThat(p.role==='student','Choisissez un profil élève.');const v=offer(s,data.id);
      requireThat(available(s,v),'Ce stage n’accepte plus de candidatures.');
      requireThat(!s.applications.some(a=>a.offerId===v.id&&a.userId===p.id&&a.status!=='withdrawn'),'Vous avez déjà candidaté à ce stage.');
      requireThat(clean(data.message).length>=10,'Écrivez quelques mots de motivation (10 caractères minimum).');
      s.applications.push({id:uid(),offerId:v.id,userId:p.id,message:clean(data.message,1500),status:'pending',created:new Date().toISOString()});
    } else if(action==='application-status') {
      const a=s.applications.find(x=>x.id===data.id);requireThat(a,'Candidature introuvable.'); const v=offer(s,a.offerId);
      requireThat(a.status!=='withdrawn','Cette candidature a été retirée.');
      if(data.status==='withdrawn')requireThat(a.userId===p.id,'Accès refusé.');
      else {requireThat(manage(s,org(s,v.orgId)),'Accès refusé.');requireThat(['pending','accepted','rejected'].includes(data.status),'Statut invalide.');
        if(data.status==='accepted'&&a.status!=='accepted')requireThat(available(s,v),'Aucune place disponible ou stage fermé.');}
      a.status=data.status;
    } else if(action==='feature') {requireThat(p.role==='admin','Accès refusé.');const o=org(s,data.id);o.featured=!o.featured;}
    else throw new Error('Action inconnue.');
    s.log.unshift({id:uid(),actor:p.name,action,created:new Date().toISOString()});s.log=s.log.slice(0,50);
  }
  function transact(state,storage,action,data) {
    const next=copy(state); apply(next,action,data); storage.setItem(KEY,JSON.stringify(next)); return next;
  }
  return {KEY,initial,load,valid,actor,manage,remaining,available,apply,transact,normalize,date};
})();
if(typeof module!=='undefined') module.exports=CesaireModel;
