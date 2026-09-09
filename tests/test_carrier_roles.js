// Run with node tests/test_carrier_roles.js. Exercises the actual inline UI code.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
assert.equal(html, fs.readFileSync(path.join(root, 'docs/index.html'), 'utf8'));
for (const [, script] of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
  new vm.Script(script); // Syntax-check every inline script, not just extracted helpers.
}
const code = html.slice(html.indexOf('function carrierAms('), html.indexOf('function afterSelect('));
const index = html.match(/const ALL_IDX = .*;/)[0];
const row = (name, role, am='Owner') => [name, role, am, 9999, 8888, 7777, 6666, 'due', 12, 34, 5555];
const carriers = [row('Both A','both'), row('Both B','both'), row('Customer','customer'),
  row('Provider','provider'), row('Idle','both'), row('Other AM','both','Other')];
const snapshot = JSON.stringify(carriers);
const sandbox = {CARR:{list:carriers}, DAILY:{dates:['2026-08-03','2026-09-03','2026-09-09'], byCarrier:{
  'Both A': [[0,100,10,20,2,80,8,200,20],[1,30,3,60,6,40,-4,400,40],[2,50,5,100,10,60,6,600,60]],
  'Both B': [[1,90,9,180,18,10,1,10,1]],
  'Customer': [[1,60,6,120,12,900,90,900,90]],
  'Provider': [[1,800,80,800,80,20,2,20,2]],
  'Other AM': [[1,1,1,1,1,1,1,1,1]]
}}, roleFilter:'customer', dateMonth:'',dateDay:'',carrierAmFilter:'Owner',
  carrierQuery:'',profitFilter:'all',sortField:null,sortDir:-1,
  summaryBar:{style:{},innerHTML:''},body:{innerHTML:''},resultCountEl:{textContent:''},
  fmtInt:v=>String(v),fmtProfit:v=>String(v),fmtExposure:v=>String(v)};
vm.createContext(sandbox);
vm.runInContext(index+'\n'+code,sandbox);
const run = expression => vm.runInContext(expression,sandbox);
const metrics = name => Array.from(run(`visibleCarrierList().find(r=>r[0]===${JSON.stringify(name)})`));
const expect = (name,dur,calls,rev,profit,exp) => {
  const r=metrics(name);
  assert.deepEqual([r[3],r[4],r[5],r[6],r[10]],[dur,calls,rev,profit,exp]);
};
expect('Both A',180,18,180,18,180);
assert.equal(run('visibleCarrierList().length'),4); // both + customer + idle
assert.equal(metrics('Idle')[3],0); // no fallback to combined CARR traffic
sandbox.roleFilter='provider';
expect('Both A',1200,120,180,10,180);
assert.equal(run('visibleCarrierList().length'),4);
sandbox.dateMonth='2026-09';
expect('Both A',1000,100,80,2,100);
sandbox.dateDay='3';
expect('Both A',400,40,30,-4,40);
sandbox.roleFilter='customer';
expect('Both A',60,6,30,3,40);
sandbox.dateMonth=''; // day selection across months
expect('Both A',80,8,130,13,120);
sandbox.dateMonth='2026-10';
expect('Both A',0,0,0,0,0);
sandbox.dateMonth='2026-09'; sandbox.dateDay='3';
function renderedNames(){
  run('renderRowsAll()');
  return [...sandbox.body.innerHTML.matchAll(/class="provider-name">([^<]+)</g)].map(m=>m[1]);
}
for(const field of ['dur','calls','profit','rev','act']){
  sandbox.sortField=field;
  assert.equal(renderedNames()[0],'Both B',field+' customer sorting');
}
assert.match(sandbox.body.innerHTML,/16\.7%/); // A: 60/(60+180+120)
assert.match(sandbox.body.innerHTML,/50\.0%/);
sandbox.roleFilter='provider';
for(const field of ['dur','calls','exp','act']){
  sandbox.sortField=field;
  assert.equal(renderedNames()[0],'Both A',field+' provider sorting');
}
sandbox.sortField='profit';
assert.deepEqual(renderedNames(),['Provider','Both B','Idle','Both A']);
assert.match(sandbox.body.innerHTML,/93\.0%/); // A: 400/(400+10+20)
sandbox.profitFilter='neg';
assert.deepEqual(renderedNames(),['Both A']);
assert.match(sandbox.body.innerHTML,/100\.0%/);
sandbox.profitFilter='all'; sandbox.carrierQuery='both b';
assert.deepEqual(renderedNames(),['Both B']);
assert.match(sandbox.body.innerHTML,/100\.0%/);
sandbox.carrierQuery='';
run('renderSummaryAll()');
assert.match(sandbox.summaryBar.innerHTML,/Period expense/);
assert.match(sandbox.summaryBar.innerHTML,/>70<\/div><div class="l">Period expense/);
sandbox.roleFilter='both';
expect('Both A',460,46,30,-1,40);
assert.equal(run("visibleCarrierList().every(r=>r[1]==='both')"),true);
sandbox.roleFilter='all'; sandbox.dateMonth=''; sandbox.dateDay='';
assert.equal(run('baseCarrierList()'),carriers); // preserve existing unfiltered combined data
sandbox.dateMonth='2026-09'; sandbox.dateDay='3';
expect('Both A',460,46,30,3,40); // preserve existing date-filtered All behavior
assert.equal(JSON.stringify(carriers),snapshot,'UI must not mutate source records');
// A role switch must not keep sorting by the newly hidden money column.
sandbox.chip={dataset:{role:'provider'}};
sandbox.setActiveFilterChips=()=>{};
sandbox.renderHead=()=>{};
sandbox.allColumns=()=>[];
const handlerStart=html.indexOf("document.querySelectorAll('#roleGroup .fchip').forEach(chip=>{");
const handler=html.slice(html.indexOf('  chip.onclick=',handlerStart),html.indexOf('\n});',handlerStart));
vm.runInContext(handler,sandbox);
sandbox.sortField='rev';
run('chip.onclick()');
assert.equal(sandbox.sortField,'exp');
sandbox.chip.dataset.role='customer';
run('chip.onclick()');
assert.equal(sandbox.sortField,'rev');
// Contractual summary fixture: membership counts must survive role/date/search changes.
sandbox.CARR.list = Array.from({length:389},(_,i)=>row('Both '+i,'both'))
  .concat(Array.from({length:23},(_,i)=>row('Customer '+i,'customer')))
  .concat(Array.from({length:7},(_,i)=>row('Provider '+i,'provider')));
for(const role of ['all','customer','provider','both']){
  sandbox.roleFilter=role; sandbox.dateMonth='2027-01'; sandbox.carrierQuery='missing';
  run('renderSummaryAll()');
  for(const [label,count] of [['Total carriers',419],['As customer',412],['As provider',396],
    ['Both (counted once)',389],['Customer only',23],['Provider only',7]]){
    assert.ok(sandbox.summaryBar.innerHTML.includes(`>${count}</div><div class="l">${label}</div>`),role+' '+label);
  }
}
console.log('PASS: mirrored HTML, JS syntax, role metrics, dates, zero traffic, sorting, activity, AM/search/profit filters, contractual counts, immutable data');
