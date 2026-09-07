const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');

// Runtime/template smoke checks; no browser or network required.
function runtime() {
 const elements=new Map(),values=new Map();
 const element=selector=>{if(!elements.has(selector))elements.set(selector,{innerHTML:'',textContent:'',open:false,dataset:{},addEventListener(){},focus(){},showModal(){this.open=true;},close(){this.open=false;}});return elements.get(selector);};
 const localStorage={getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};
 const document={querySelector:element,querySelectorAll:()=>[],addEventListener(){},documentElement:{dataset:{}},title:''};
 const context={document,location:{hash:''},window:{localStorage,addEventListener(){},scrollTo(){}},setTimeout:()=>0,clearTimeout(){},console};
 vm.createContext(context);
 for(const file of ['data.js','model.js','app.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'..',file),'utf8'),context,{filename:file});
 return {context,elements,run:code=>vm.runInContext(code,context)};
}
test('all routes render for each local role without runtime errors',()=>{
 const r=runtime();
 for(const profile of ['student','representative','admin']){
  r.run(`state.current='${profile}'`);
  for(const route of ['explorer','carte','organisations','organisation/1','stage/offer-1','favoris','candidatures','espace','guide','confidentialite','missing']){
   r.context.location.hash='#'+route;r.run('render()');
   assert.ok(r.elements.get('#main').innerHTML.length>100,profile+':'+route);
   assert.ok(!r.elements.get('#main').innerHTML.includes('undefined'),profile+':'+route);
  }
 }
});
test('filter by accented sector, dates and query works',()=>{
 const r=runtime();
 r.run("filters.query='education'");assert.ok(r.run('filterResults().length')>0);
 r.run("filters.start='2099-01-01'");assert.equal(r.run('filterResults().length'),0);
 r.run("filters.start='';filters.query='no such company 987'");assert.equal(r.run('filterResults().length'),0);
});
test('stored text cannot inject markup into cards or detail templates',()=>{
 const r=runtime();r.run(`state.orgs[0].name='<img src=x onerror=alert(1)>';state.offers[0].title='<script>alert(1)</script>'`);
 const card=r.run('offerCard(state.offers[0])');
 assert.ok(card.includes('&lt;script&gt;'));assert.ok(!card.includes('<script>'));assert.ok(!card.includes('<img'));
 assert.ok(!r.run("detail('offer-1')").includes('<img'));
});
test('application simulation is reflected in student and organization templates',()=>{
 const r=runtime();
 r.run("M.apply(state,'apply',{id:'offer-1',message:'Je souhaite découvrir ce métier.'})");
 assert.ok(r.run('studentApplications()').includes('En attente'));
 r.run("state.current='admin';selectedOrg='1'");assert.ok(r.run('workspace()').includes('Je souhaite découvrir ce métier.'));
 r.run("M.apply(state,'application-status',{id:state.applications[0].id,status:'accepted'});state.current='student'");
 assert.ok(r.run('studentApplications()').includes('Acceptée'));
});
test('native forms and referenced assets exist without third-party requests',()=>{
 const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
 for(const [,file]of html.matchAll(/(?:src|href)="([^"#]+\.(?:js|css))"/g))assert.ok(fs.existsSync(path.join(__dirname,'..',file)),file);
 assert.ok(!html.includes('https://'));
 const r=runtime();r.run("state.current='representative';orgForm()");
 assert.ok(r.elements.get('#dialog-body').innerHTML.includes('data-form="org-save"'));
 r.run("state.current='admin';offerForm('1')");
 assert.ok(r.elements.get('#dialog-body').innerHTML.includes('type="date"'));
});
test('map renders real addresses and explicit fictional-offer labels',()=>{
 const r=runtime();
 assert.ok(r.run('mapView()').includes('OpenStreetMap'));
 assert.ok(r.run('mapView()').includes('Mairie de Clisson'));
 assert.ok(r.run('offerCard(state.offers[0])').includes('Offre fictive'));
 assert.ok(r.run("detail('offer-1')").includes('ne constitue pas un partenariat'));
});
