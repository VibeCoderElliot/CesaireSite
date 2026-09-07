'use strict';

const M = CesaireModel;
const $ = selector => document.querySelector(selector);
const e = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels = {student:'Élève',representative:'Organisation',admin:'Administration',approved:'Approuvée localement',pending:'En attente',rejected:'Refusée',blocked:'Suspendue',draft:'Brouillon',published:'Visible localement',paused:'En pause',archived:'Archivé',accepted:'Acceptée',withdrawn:'Retirée'};
let state, storage, storageBlocked = false, toastTimer;
try { storage = window.localStorage; state = M.load(storage,companies); }
catch { state = M.initial(companies); storageBlocked = true; }
let filters = {query:'',sector:'',metro:'',start:'',end:'',sort:'recommended',onlyAvailable:false};
let selectedOrg = '';
const person = () => M.actor(state);
const getOrg = id => state.orgs.find(o=>o.id===id);
const getOffer = id => state.offers.find(o=>o.id===id);
const initials = name => String(name).split(/\s+/).slice(0,2).map(s=>s[0]||'').join('').toUpperCase();
const fmt = value => value ? new Date(value+'T12:00:00').toLocaleDateString('fr-FR',{day:'numeric',month:'short',year:'numeric'}) : 'À convenir';
const period = o => o.start ? fmt(o.start)+' — '+fmt(o.end) : 'Dates à convenir';
const tag = (status) => '<span class="tag '+(['accepted','approved','published'].includes(status)?'green':['pending','paused'].includes(status)?'orange':'')+'">'+e(labels[status]||status)+'</span>';
const btn = (action,id,text,cls='secondary',extra='') => '<button type="button" class="'+cls+'" data-action="'+action+'" data-id="'+e(id)+'" '+extra+'>'+text+'</button>';
const empty = (title,text,link='#explorer',cta='Explorer les stages') => '<div class="empty"><h2>'+title+'</h2><p>'+text+'</p><a class="button" href="'+link+'">'+cta+'</a></div>';
const title = (heading,sub='',eyebrow='LYCÉE AIMÉ CÉSAIRE') => '<div class="page-title"><span class="eyebrow">'+eyebrow+'</span><h1>'+heading+'</h1><p>'+sub+'</p></div>';
const options = (values,current='',placeholder='') => (placeholder?'<option value="">'+placeholder+'</option>':'')+values.map(v=>{const [value,name]=Array.isArray(v)?v:[v,v];return '<option value="'+e(value)+'"'+(String(value)===String(current)?' selected':'')+'>'+e(name)+'</option>';}).join('');
const field = (name,label,value='',type='text',required=true,full=false) => '<label class="'+(full?'full':'')+'">'+label+'<input name="'+name+'" type="'+type+'" value="'+e(value)+'" '+(required?'required':'')+' maxlength="200"></label>';
const area = (name,label,value='',required=false) => '<label class="full">'+label+'<textarea name="'+name+'" maxlength="1500" '+(required?'required':'')+'>'+e(value)+'</textarea></label>';
const select = (name,label,values,current) => '<label>'+label+'<select name="'+name+'">'+options(values,current)+'</select></label>';
function toast(message) {clearTimeout(toastTimer);$('#toast').textContent=message;toastTimer=setTimeout(()=>{$('#toast').textContent='';},6500);}
function mutate(action,data,message) {
  try {if(storageBlocked) throw new Error('Stockage indisponible : aucune donnée modifiée. Consultez Données & fonctionnement.');
    state=M.transact(state,storage,action,data);
    if($('#dialog').open)$('#dialog').close();
    render(); if(message)toast(message); return true;
  } catch(error) { const box=$('#dialog[open] .error'); if(box)box.textContent=error.message;else toast(error.message);return false; }
}
function dialog(heading,body) {$('#dialog-title').textContent=heading;$('#dialog-body').innerHTML=body;if(!$('#dialog').open)$('#dialog').showModal();}
function form(action,fields,id='',orgId='',submit='Enregistrer') {return '<form data-form="'+action+'" data-id="'+e(id)+'" data-org="'+e(orgId)+'"><p class="form-note">Simulation locale. N’utilisez pas de données personnelles réelles.</p><div class="form-grid">'+fields+'</div><p class="error" role="alert"></p><div class="form-actions">'+btn('close','', 'Annuler')+'<button class="button" type="submit">'+submit+'</button></div></form>';}
function profiles() {return '<label>Profil de démonstration<select id="profile-select">'+options(state.profiles.map(p=>[p.id,labels[p.role]+' · '+p.name]),state.current)+'</select></label>';}
function saved(id) {return state.favorites.some(f=>f.userId===state.current&&f.offerId===id);}
function offerCard(o) {
 const org=getOrg(o.orgId),open=M.available(state,o);
 return '<article class="card"><div class="card-top"><span class="monogram" aria-hidden="true">'+e(initials(org.name))+'</span>'+btn('favorite',o.id,saved(o.id)?'♥':'♡','icon-button','aria-label="Enregistrer ce stage" aria-pressed="'+saved(o.id)+'"')+'</div><div class="tags"><span class="tag">'+e(org.sector)+'</span>'+(org.featured?'<span class="badge">À découvrir</span>':'')+'</div><div><h3><a href="#stage/'+e(o.id)+'">'+e(o.title)+'</a></h3><p class="org-name">'+e(org.name)+'</p></div><p class="description">'+e(o.description)+'</p><div class="meta"><span>Ⓜ '+e(org.metro||'Station non précisée')+'</span><span>▦ '+e(period(o))+'</span><span>◷ '+e(o.duration||'Durée selon la période')+'</span></div><div class="card-bottom"><span class="tag '+(open?'green':'')+'">'+(open?M.remaining(state,o)+' place(s)':'Indisponible')+'</span><a href="#stage/'+e(o.id)+'">Voir le stage ↗</a></div></article>';
}
function publicOffers() {return state.offers.filter(o=>o.status==='published'&&getOrg(o.orgId)?.status==='approved');}
function filterResults() {
 let rows=publicOffers().filter(o=>{
  const g=getOrg(o.orgId);
  return (!filters.query||M.normalize([o.title,g.name,o.description,g.sector].join(' ')).includes(M.normalize(filters.query)))&&
   (!filters.sector||g.sector===filters.sector)&&(!filters.metro||g.metro===filters.metro)&&
   (!filters.start||(o.start&&o.start<=filters.start&&o.end>=filters.start))&&
   (!filters.end||(o.end&&o.end>=filters.end&&o.start<=filters.end))&&
   (!filters.onlyAvailable||M.available(state,o));
 });
 rows.sort((a,b)=> filters.sort==='date'?(a.start||'9999').localeCompare(b.start||'9999'):filters.sort==='name'?getOrg(a.orgId).name.localeCompare(getOrg(b.orgId).name,'fr'):Number(!!getOrg(b.orgId).featured)-Number(!!getOrg(a.orgId).featured)||b.created.localeCompare(a.created));
 return rows;
}
function renderResults() {
 const rows=filterResults(); $('#results-count').textContent=rows.length+' stage'+(rows.length!==1?'s':'');
 $('#results').innerHTML=rows.length?rows.map(offerCard).join(''):empty('Aucun stage trouvé','Essayez un autre secteur ou une période différente. Les stages sans dates précises ne sont pas affichés avec un filtre de dates.','#explorer','Revenir au catalogue');
}
function explorer() {
 const sectors=[...new Set(state.orgs.map(o=>o.sector))].sort(),metros=[...new Set(state.orgs.map(o=>o.metro).filter(Boolean))].sort();
 return '<section class="intro"><div><span class="eyebrow">TON LYCÉE. TON AVENIR.</span><h1>Le premier pas,<br><em>c’est ton stage.</em></h1><p>Découvre des métiers et prépare ton expérience professionnelle avec le projet Césaire Stages.</p></div><aside class="school-card"><span class="eyebrow">AIMÉ CÉSAIRE</span><div class="number">'+publicOffers().length+'</div><p>stages dans le catalogue local.<br>À toi de trouver ta voie.</p><a href="#guide">Préparer ma candidature ↗</a></aside></section>'+
 '<form class="search-bar" id="search-form"><span class="search-symbol" aria-hidden="true">⌕</span><label class="visually-hidden" for="query">Rechercher un métier ou une organisation</label><input id="query" placeholder="Un métier, une organisation…" value="'+e(filters.query)+'"><button class="button lime">Rechercher</button></form>'+
 '<div class="catalog-layout"><aside class="filters" id="filters"><h2>Affiner ma recherche</h2><label>Secteur<select data-filter="sector">'+options(sectors,filters.sector,'Tous les secteurs')+'</select></label><label>Station de métro<select data-filter="metro">'+options(metros,filters.metro,'Toutes les stations')+'</select></label><label>Début souhaité<input type="date" data-filter="start" value="'+e(filters.start)+'"></label><label>Fin souhaitée<input type="date" data-filter="end" value="'+e(filters.end)+'"></label><label class="check-label"><input type="checkbox" data-filter="onlyAvailable" '+(filters.onlyAvailable?'checked':'')+'>Places disponibles</label>'+btn('reset-filters','','Tout effacer')+'</aside><section aria-label="Résultats"><div class="section-head"><h2 id="results-count" aria-live="polite"></h2>'+btn('filters','','Filtres','secondary mobile-filter','aria-controls="filters" aria-expanded="false"')+'<label><span class="visually-hidden">Trier les résultats</span><select data-filter="sort">'+options([['recommended','Notre sélection'],['date','Date de début'],['name','Organisation A–Z']],filters.sort)+'</select></label></div><p class="form-note">Catalogue de démonstration : coordonnées et disponibilités non vérifiées.</p><div class="cards" id="results"></div></section></div>'+
 '<section class="cta-strip"><div><h2>Une place pour les talents de demain.</h2><p>Créez votre organisation ou demandez à gérer sa fiche existante.</p></div><a class="button lime" href="#organisations">Espace organisations ↗</a></section>';
}
function detail(id) {
 const o=getOffer(id),g=o&&getOrg(o.orgId);
 if(!o||!g||(o.status!=='published'&&!M.manage(state,g))||(g.status!=='approved'&&!M.manage(state,g)))return empty('Stage indisponible','Cette offre n’est pas accessible dans le catalogue.');
 const already=state.applications.some(a=>a.offerId===id&&a.userId===state.current&&a.status!=='withdrawn');
 const list=t=>'<ul>'+String(t||'À préciser avec l’organisation.').split('\n').filter(Boolean).map(l=>'<li>'+e(l)+'</li>').join('')+'</ul>';
 return '<a class="back" href="#explorer">← Tous les stages</a>'+title(e(o.title),e(g.name),'DÉCOUVRIR · '+e(g.sector))+
 '<div class="detail-grid"><div><section class="panel"><h2>Une expérience à découvrir</h2><p class="prewrap">'+e(o.description)+'</p><h3>Ce que tu feras</h3>'+list(o.tasks)+'<h3>Ce qu’on attend de toi</h3>'+list(o.requirements)+'</section><section class="panel"><h2>'+e(g.name)+'</h2><p>'+e(g.description)+'</p><p class="muted">'+e(g.address)+'</p><a class="text-link" href="#organisation/'+e(g.id)+'">Voir l’organisation</a></section></div><aside class="panel detail-sidebar"><h2>En pratique</h2><dl><dt>Période</dt><dd>'+e(period(o))+'</dd><dt>Durée</dt><dd>'+e(o.duration||'Selon la période')+'</dd><dt>Horaires</dt><dd>'+e(o.schedule||'À convenir')+'</dd><dt>Accès</dt><dd>Ⓜ '+e(g.metro||'À préciser')+'</dd><dt>Places restantes</dt><dd>'+M.remaining(state,o)+'</dd></dl>'+btn('apply',id,already?'Candidature enregistrée':'Candidater localement','button',(!M.available(state,o)||already?'disabled':''))+btn('favorite',id,saved(id)?'♥ Enregistré':'♡ Enregistrer')+'<p class="form-note">Aucune candidature n’est envoyée à une entreprise. Ceci est une simulation.</p></aside></div>';
}
function organizations(id) {
 if(id) {
  const o=getOrg(id);if(!o)return empty('Organisation introuvable','Revenez au catalogue.','#organisations','Voir les organisations');
  if(o.status!=='approved'&&!M.manage(state,o))return empty('Fiche en cours de vérification','Elle apparaîtra après approbation locale.','#organisations','Voir les organisations');
  const rows=publicOffers().filter(v=>v.orgId===id);
  return '<a class="back" href="#organisations">← Les organisations</a>'+title(e(o.name),e(o.description),e(o.sector))+
   '<section class="panel"><div class="section-head"><div><p>'+e(o.address)+'</p><p>Ⓜ '+e(o.metro||'Station à préciser')+'</p></div>'+ (M.manage(state,o)?'<a class="button" href="#espace/'+e(o.id)+'">Gérer cette organisation</a>':!o.owner?btn('claim',id,'Demander à gérer cette fiche'):tag('approved'))+'</div><p class="form-note">Coordonnées du catalogue, non vérifiées : '+e(o.email||'Email à préciser')+' · '+e(o.phone||'Téléphone à préciser')+'</p></section><div class="cards">'+(rows.length?rows.map(offerCard).join(''):empty('Pas encore de stage','Cette organisation n’a pas de stage visible pour le moment.'))+'</div>';
 }
 const rows=state.orgs.filter(o=>o.status==='approved');
 return title('Des rencontres qui ouvrent des portes.','Explore les organisations du catalogue ou ajoute ta structure.')+
  '<div class="section-head"><p>'+rows.length+' organisations · fiches de démonstration</p>'+btn('org-new','','Ajouter une organisation','button')+'</div><div class="cards">'+rows.map(o=>'<article class="card"><div class="card-top"><span class="monogram">'+e(initials(o.name))+'</span><span class="tag">'+e(o.sector)+'</span></div><h3><a href="#organisation/'+e(o.id)+'">'+e(o.name)+'</a></h3><p class="description">'+e(o.description)+'</p><p class="meta">Ⓜ '+e(o.metro||'À préciser')+'</p><div class="card-bottom"><a href="#organisation/'+e(o.id)+'">Voir la fiche ↗</a>'+(!o.owner?btn('claim',o.id,'Gérer cette fiche','secondary small'):'<span class="tag">Fiche attribuée</span>')+'</div></article>').join('')+'</div>';
}
function studentApplications() {
 const rows=state.applications.filter(a=>a.userId===state.current);
 return rows.length?'<section class="panel"><h2>Mes candidatures</h2>'+rows.map(a=>{const o=getOffer(a.offerId);return '<div class="row"><div><h3><a href="#stage/'+e(o.id)+'">'+e(o.title)+'</a></h3><p>'+e(getOrg(o.orgId).name)+' · '+fmt(a.created.slice(0,10))+'</p>'+tag(a.status)+'</div>'+(a.status!=='withdrawn'?btn('withdraw',a.id,'Retirer'):'')+'</div>';}).join('')+'</section>':empty('Ta prochaine expérience commence ici.','Tu n’as pas encore de candidature locale. Trouve une offre et écris quelques mots de motivation.');
}
function profileForm() {
 const p=person();
 return '<section class="panel"><h2>Mon profil local</h2>'+form('profile',field('name','Prénom ou pseudonyme',p.name)+field('classroom','Classe',p.classroom||'','text',false)+area('interests','Métiers qui m’intéressent',p.interests||''),'','','Enregistrer mon profil')+'</section>';
}
function workspace(id) {
 const p=person();if(id)selectedOrg=id;
 const tabs='<nav class="tabs" aria-label="Mon espace"><a href="#espace">Vue d’ensemble</a><a href="#favoris">Mes favoris</a><a href="#candidatures">Mes candidatures</a><a href="#organisations">Organisations</a></nav>';
 let body=title('Mon espace.','Un point de départ pour chaque étape de ton stage.')+'<div class="workspace-top">'+profiles()+btn('export','','Exporter mes données')+'</div>'+tabs;
 if(p.role==='student') {
  const f=state.favorites.filter(f=>f.userId===p.id).length,a=state.applications.filter(a=>a.userId===p.id&&a.status!=='withdrawn');
  return body+'<div class="stats"><div class="stat"><strong>'+f+'</strong><span>Stages enregistrés</span></div><div class="stat"><strong>'+a.length+'</strong><span>Candidatures locales</span></div><div class="stat"><strong>'+a.filter(x=>x.status==='accepted').length+'</strong><span>Réponses positives</span></div></div>'+profileForm()+studentApplications();
 }
 const owned=state.orgs.filter(o=>M.manage(state,o));
 if(!owned.some(o=>o.id===selectedOrg))selectedOrg=owned[0]?.id||'';
 body+='<div class="section-head"><h2>'+ (p.role==='admin'?'Administration locale':'Mes organisations')+'</h2>'+btn('org-new','','Ajouter une organisation','button')+'</div>';
 if(p.role==='admin') body+=moderation();
 if(p.role==='representative')body+=claimHistory();
 if(!owned.length)return body+empty('Votre organisation, votre espace.','Ajoutez votre structure ou demandez les droits sur une fiche déjà créée.','#organisations','Trouver mon organisation');
 const g=getOrg(selectedOrg);
 const offers=state.offers.filter(o=>o.orgId===g.id);
 const apps=state.applications.filter(a=>offers.some(o=>o.id===a.offerId));
 body+='<section class="panel"><label>Organisation active<select id="org-select">'+options(owned.map(o=>[o.id,o.name]),g.id)+'</select></label><div class="section-head spacing"><div><h2>'+e(g.name)+'</h2>'+tag(g.status)+'</div><div class="row-actions">'+btn('org-edit',g.id,'Modifier la fiche')+btn('offer-new',g.id,'Créer un stage','button')+'</div></div><p>'+e(g.description)+'</p></section>';
 body+='<div class="stats"><div class="stat"><strong>'+offers.length+'</strong><span>Stages</span></div><div class="stat"><strong>'+apps.filter(a=>a.status==='pending').length+'</strong><span>Candidatures à traiter</span></div><div class="stat"><strong>'+apps.filter(a=>a.status==='accepted').length+'</strong><span>Candidatures acceptées</span></div></div>';
 body+='<section class="panel"><h2>Stages de l’organisation</h2>'+(offers.length?offers.map(o=>'<div class="row"><div><h3>'+e(o.title)+'</h3><p>'+e(period(o))+' · '+M.remaining(state,o)+' place(s) restante(s)</p>'+tag(o.status)+'</div><div class="row-actions">'+btn('offer-edit',o.id,'Modifier')+(o.status==='published'?btn('pause',o.id,'Pause'):'')+(o.status!=='archived'?btn('archive',o.id,'Archiver'):'')+'</div></div>').join(''):'<p class="muted">Créez votre première offre avec une période et un nombre de places.</p>')+'</section>';
 body+='<section class="panel"><h2>Candidatures reçues localement</h2>'+(apps.length?apps.map(a=>'<div class="row"><div><h3>'+e(state.profiles.find(p=>p.id===a.userId)?.name||'Élève')+'</h3><p>'+e(getOffer(a.offerId).title)+'</p><p class="prewrap">'+e(a.message)+'</p>'+tag(a.status)+'</div>'+(a.status!=='withdrawn'?'<div class="row-actions">'+btn('accept',a.id,'Accepter','button small')+btn('reject-app',a.id,'Refuser','secondary small')+'</div>':'')+'</div>').join(''):'<p class="muted">Les candidatures créées avec un profil élève apparaîtront ici.</p>')+'</section>';
 return body;
}
function claimHistory() {
 const rows=state.claims.filter(c=>c.userId===state.current);
 return rows.length?'<section class="panel"><h2>Mes demandes de gestion</h2>'+rows.map(c=>'<div class="row"><div><h3>'+e(getOrg(c.orgId)?.name)+'</h3><p>'+e(c.reason)+'</p></div>'+tag(c.status)+'</div>').join('')+'</section>':'';
}
function moderation() {
 const orgs=state.orgs.filter(o=>o.status==='pending'), claims=state.claims.filter(c=>c.status==='pending');
 return '<section class="panel"><h2>À vérifier · '+(orgs.length+claims.length)+'</h2>'+(!orgs.length&&!claims.length?'<p class="muted">Tout est à jour. Les nouvelles organisations et demandes de gestion apparaîtront ici.</p>':'')+
 orgs.map(o=>'<div class="row"><div><h3>'+e(o.name)+'</h3><p>Nouvelle organisation · '+e(o.address)+'</p></div><div class="row-actions">'+btn('approve-org',o.id,'Approuver','button small')+btn('reject-org',o.id,'Refuser','secondary small')+'</div></div>').join('')+
 claims.map(c=>'<div class="row"><div><h3>'+e(getOrg(c.orgId)?.name)+'</h3><p>Demande de gestion · '+e(state.profiles.find(p=>p.id===c.userId)?.name)+'</p><p>'+e(c.reason)+'</p></div><div class="row-actions">'+btn('approve-claim',c.id,'Accorder','button small')+btn('reject-claim',c.id,'Refuser','secondary small')+'</div></div>').join('')+'</section>'+
 '<details class="panel"><summary>Statut des organisations & sélection</summary>'+state.orgs.map(o=>'<div class="row"><div><h3>'+e(o.name)+'</h3>'+tag(o.status)+'</div><div class="row-actions">'+btn('feature',o.id,o.featured?'Retirer de la sélection':'Mettre en avant','secondary small')+(o.status==='approved'?btn('block-org',o.id,'Suspendre','secondary small'):btn('approve-org',o.id,'Approuver','secondary small'))+'</div></div>').join('')+'</details>';
}
function guide() {return title('Un stage, ça se prépare.','Trois étapes pour avancer sereinement, avec ton équipe pédagogique.')+'<div class="guide-grid">'+[['01','Trouve ce qui te plaît','Explore les métiers et les organisations. Vérifie les dates prévues par ton lycée avant de contacter une structure.'],['02','Prépare ta candidature','Présente-toi, indique ta classe et tes disponibilités. Explique ce que tu aimerais découvrir et pourquoi cette organisation t’intéresse.'],['03','Confirme avec ton lycée','Fais valider ton accueil et les documents nécessaires par ton équipe pédagogique avant le début du stage.']].map(([n,h,p])=>'<article class="panel"><span class="step">'+n+'</span><h2>'+h+'</h2><p>'+p+'</p></article>').join('')+'</div><section class="panel"><h2>Les réponses utiles</h2><details><summary>Est-ce que ma candidature est envoyée ?</summary><p>Non. Cette version fonctionne uniquement dans ton navigateur. Elle permet de tester les étapes, pas de contacter une organisation.</p></details><details><summary>Comment une organisation récupère sa fiche ?</summary><p>Choisis le profil Organisation dans Mon espace, ouvre sa fiche et demande à la gérer. Le profil Administration peut ensuite approuver la demande localement.</p></details><details><summary>Où retrouver mes données ?</summary><p>Dans le même navigateur. Elles ne sont pas synchronisées entre appareils. Tu peux les exporter dans Mon espace.</p></details><details><summary>Est-ce un service officiel du lycée ?</summary><p>Césaire Stages est un projet conçu pour les élèves du lycée Aimé Césaire. Aucun statut officiel ni partenariat n’est revendiqué.</p></details></section>';}
function privacy() {return title('Tes données restent ici.','Une version locale, sans compte distant ni service connecté.')+'<section class="panel"><h2>Ce qui est enregistré</h2><p>Profils de démonstration, favoris, organisations, stages, demandes de gestion et candidatures sont stockés dans ce navigateur. Aucun mot de passe n’est demandé.</p><p>Toute personne utilisant ce navigateur peut changer de profil et accéder aux données locales. Ce n’est pas une authentification sécurisée. N’ajoute ni pièce d’identité, ni document confidentiel, ni données réelles d’élèves.</p><p>Effacer les données du navigateur peut supprimer ce travail. L’export permet de conserver une copie JSON, mais cette version ne propose pas encore d’import.</p><div class="form-actions">'+btn('export','','Exporter les données')+btn('reset','','Effacer les données de cette version','danger')+'</div></section>';}
function render() {
 const [route,id]=location.hash.slice(1).split('/');
 let content;
 if(!route||route==='explorer') content=explorer();
 else if(route==='stage') content=detail(id);
 else if(route==='organisations'||route==='organisation')content=organizations(route==='organisation'?id:null);
 else if(route==='espace')content=workspace(id);
 else if(route==='favoris') {const rows=state.offers.filter(o=>saved(o.id)&&getOrg(o.orgId)?.status==='approved'&&o.status==='published');content=title('Les stages qui te ressemblent.','Ta sélection, à retrouver dans ce navigateur.')+'<div class="workspace-top">'+profiles()+'</div><div class="cards">'+(rows.length?rows.map(offerCard).join(''):empty('Garde une longueur d’avance.','Appuie sur le cœur d’une offre pour la retrouver ici.'))+'</div>';}
 else if(route==='candidatures')content=title('Chaque candidature, une avancée.','Suis tes démarches locales et les réponses des organisations.')+'<div class="workspace-top">'+profiles()+'</div>'+studentApplications();
 else if(route==='guide')content=guide();
 else if(route==='confidentialite')content=privacy();
 else content=empty('Cette page n’existe pas.','Reviens au catalogue pour poursuivre ta recherche.');
 $('#main').innerHTML=(storageBlocked?'<p class="notice" role="alert">Sauvegarde locale indisponible ou données incompatibles. Mode lecture seule ; les données existantes ne sont pas écrasées.</p>':'')+content;
 if(!route||route==='explorer') renderResults();
 document.querySelectorAll('nav a').forEach(a=>{const active=a.getAttribute('href')==='#'+(route||'explorer');if(active)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
 document.title=(route==='stage'&&getOffer(id)?getOffer(id).title+' · ':'')+'Césaire Stages · Lycée Aimé Césaire';
}
function rolePrompt(role) {dialog('Choisir le bon espace','<p class="form-note">Cette action utilise le profil '+e(labels[role])+'. Les profils sont des simulations locales, sans mot de passe.</p>'+btn('switch',role,'Utiliser le profil '+e(labels[role]),'button')); }
function orgForm(id='') {
 const g=getOrg(id)||{};
 if(person().role==='student')return rolePrompt('representative');
 dialog(id?'Modifier l’organisation':'Ajouter une organisation',form('org-save',field('name','Nom de l’organisation',g.name)+field('sector','Secteur',g.sector)+field('metro','Station de métro',g.metro,'text',false)+field('address','Adresse',g.address)+field('email','Email de contact fictif',g.email,'email',false)+field('phone','Téléphone fictif',g.phone,'tel',false)+area('description','Présentation',g.description,true),id,'',id?'Enregistrer':'Créer la fiche locale'));
}
function offerForm(orgId,id='') {
 const o=getOffer(id)||{};
 dialog(id?'Modifier le stage':'Créer un stage',form('offer-save',field('title','Titre du stage',o.title)+select('status','Visibilité',[['draft','Brouillon'],['published','Visible localement'],['paused','En pause'],['archived','Archivé']],o.status||'draft')+field('start','Date de début',o.start,'date')+field('end','Date de fin',o.end,'date')+field('capacity','Nombre de places',o.capacity||1,'number')+field('duration','Durée (ex. 2 semaines)',o.duration,'text',false)+field('schedule','Horaires',o.schedule,'text',false,true)+area('description','Description',o.description,true)+area('tasks','Missions (une par ligne)',o.tasks)+area('requirements','Prérequis (un par ligne)',o.requirements),id,orgId));
}
function exportData() {
 const blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');
 a.href=url;a.download='cesaire-stages-local.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Copie locale exportée. Conservez-la sur un appareil de confiance.');
}
document.addEventListener('click',event=>{
 const b=event.target.closest('[data-action]');if(!b)return;const {action,id}=b.dataset;
 if(action==='close')return $('#dialog').close();
 if(action==='switch')return mutate('switch',{id},'Profil local changé. Relancez l’action souhaitée.');
 if(action==='filters'){const open=$('#filters').classList.toggle('open');b.setAttribute('aria-expanded',String(open));return;}
 if(action==='reset-filters'){filters={query:'',sector:'',metro:'',start:'',end:'',sort:'recommended',onlyAvailable:false};return render();}
 if(action==='favorite'){if(person().role!=='student')return rolePrompt('student');return mutate('favorite',{id},saved(id)?'Stage retiré des favoris.':'Stage enregistré.');}
 if(action==='org-new'||action==='org-edit')return orgForm(action==='org-edit'?id:'');
 if(action==='offer-new')return offerForm(id);
 if(action==='offer-edit'){const o=getOffer(id);if(o)return offerForm(o.orgId,id);}
 if(action==='claim'){
  if(person().role!=='representative')return rolePrompt('representative');
  return dialog('Demander à gérer cette organisation',form('claim',area('reason','Votre rôle et votre lien avec cette organisation','',true),id,'','Enregistrer la demande'));
 }
 if(action==='apply'){if(person().role!=='student')return rolePrompt('student');return dialog('Ta candidature locale',form('apply',area('message','Pourquoi ce stage t’intéresse-t-il ?','',true),id,'','Enregistrer ma candidature'));}
 const actions={
  'approve-org':['org-status','approved'],'reject-org':['org-status','rejected'],'block-org':['org-status','blocked'],
  'approve-claim':['claim-review','approved'],'reject-claim':['claim-review','rejected'],
  'accept':['application-status','accepted'],'reject-app':['application-status','rejected'],
  'pause':['offer-status','paused'],'archive':['offer-status','archived']
 };
 if(actions[action]){const [kind,status]=actions[action];return mutate(kind,{id,status},'Modification enregistrée localement.');}
 if(action==='withdraw')return dialog('Retirer cette candidature ?','<p>La candidature sera marquée comme retirée dans ce navigateur.</p><div class="form-actions">'+btn('close','','Annuler')+btn('confirm-withdraw',id,'Retirer','danger')+'</div>');
 if(action==='confirm-withdraw')return mutate('application-status',{id,status:'withdrawn'},'Candidature retirée.');
 if(action==='feature')return mutate('feature',{id},'Sélection mise à jour.');
 if(action==='export')return exportData();
 if(action==='reset')return dialog('Effacer les données locales ?','<p>Les profils, stages ajoutés, favoris et demandes de cette version seront supprimés de ce navigateur. Exportez une copie avant de continuer. Le catalogue initial sera restauré.</p><div class="form-actions">'+btn('close','','Annuler')+btn('confirm-reset','','Effacer','danger')+'</div>');
 if(action==='confirm-reset'){
  try{window.localStorage.removeItem(M.KEY);storage=window.localStorage;state=M.initial(companies);storageBlocked=false;$('#dialog').close();render();toast('Données locales effacées. Le catalogue initial est restauré.');}catch{toast('Le navigateur empêche la suppression.');}
 }
});
document.addEventListener('submit',event=>{
 event.preventDefault();const f=event.target;
 if(f.id==='search-form'){filters.query=$('#query').value;renderResults();return;}
 if(!f.dataset.form)return;
 const data=Object.fromEntries(new FormData(f));data.id=f.dataset.id;data.orgId=f.dataset.org;
 mutate(f.dataset.form,data,'Enregistré dans ce navigateur.');
});
document.addEventListener('input',event=>{if(event.target.id==='query'){filters.query=event.target.value;renderResults();}});
document.addEventListener('change',event=>{
 const t=event.target;
 if(t.dataset.filter){filters[t.dataset.filter]=t.type==='checkbox'?t.checked:t.value;renderResults();}
 if(t.id==='profile-select')mutate('switch',{id:t.value},'Profil local changé.');
 if(t.id==='org-select'){selectedOrg=t.value;location.hash='espace/'+t.value;}
});
$('#close-dialog').addEventListener('click',()=>$('#dialog').close());
$('#theme').addEventListener('click',()=>{
 const dark=document.documentElement.dataset.theme!=='dark';document.documentElement.dataset.theme=dark?'dark':'light';
 try{window.localStorage.setItem('cesaire_theme',dark?'dark':'light');}catch{toast('Le thème ne pourra pas être conservé.');}
});
try{document.documentElement.dataset.theme=window.localStorage.getItem('cesaire_theme')||'light';}catch{}
window.addEventListener('hashchange',()=>{if($('#dialog').open)$('#dialog').close();render();$('#main').focus({preventScroll:true});window.scrollTo(0,0);});
window.addEventListener('storage',event=>{if(event.key===M.KEY){try{state=M.load(storage,companies);storageBlocked=false;render();toast('Données actualisées depuis un autre onglet.');}catch{storageBlocked=true;render();}}});
render();
