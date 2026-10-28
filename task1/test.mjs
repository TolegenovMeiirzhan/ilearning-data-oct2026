import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {spawnSync} from 'node:child_process';
const path=new URL('./lcs.js',import.meta.url);
const code=fs.readFileSync(path,'utf8');
function oracle(words){
  if(!words.length)return 0;
  const first=words[0];let longest=0;
  for(let begin=0;begin<first.length;begin++)for(let end=begin+1;end<=first.length;end++){
    const part=first.slice(begin,end);
    if(words.every(word=>word.indexOf(part)>=0))longest=Math.max(longest,part.length);
  }
  return longest;
}
function validate(words,actual){
  assert.equal(typeof actual,'string');
  assert.equal(actual.length,oracle(words));
  assert(words.every(word=>word.includes(actual)));
}
const cases=[[],[''],['ABCDEFZ','WBCDXYZ'],['132','12332','12312'],
['ABCDEFGH','ABCDEFG','ABCEDF','ABCED'],['ABCDEFGH','ABCDEFG','ABCDEF','ABCDE'],
['ABCDEFGH','ABCDEFG','ABCDEF','ABCDE','EDCBA'],['ABCDEFGH','ABCDEFG','ABCDEF','ABCDE','EDCBCA'],
['ABCDEFGH','ABCDEFG','AxBCDEF','ABCDxE','EDCBCAABCD'],['ABCDEFGH','1234'],['ABCDEFGH'],
['ABCQEFDEFGHIJ','BCXEFGYZBCDEWEFGHU'],['abc','ABC'],['a',''],['11111','111'],
Array(64).fill('A'.repeat(256)),['A'.repeat(256),'B'.repeat(256)]];
let seed=9713;const random=n=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed%n;};
for(let k=0;k<1000;k++){
  const words=Array.from({length:random(7)},()=>Array.from({length:random(13)},()=>'abAB01'[random(6)]).join(''));
  cases.push(words);
}
for(const words of cases){
  const output=[];vm.runInNewContext(code,{process:{argv:['node','lcs.js',...words]},console:{log:value=>output.push(value)}},{timeout:5000});
  assert.equal(output.length,1);validate(words,output[0]);
}
for(const words of cases.slice(0,17)){
  const result=spawnSync(process.execPath,[path.pathname.replace(/^\/([A-Za-z]:)/,'$1'),...words],{encoding:'utf8',timeout:5000});
  assert.equal(result.status,0,result.stderr);assert.equal(result.stderr,'');
  assert(result.stdout.endsWith('\n'));assert.equal(result.stdout.split('\n').length,2);
  validate(words,result.stdout.slice(0,-1));
}
assert(!/require|import|process\.(stdin|exit)|readline/.test(code));
console.log(`PASS: ${cases.length} oracle cases; 17 real CLI cases; ${Buffer.byteLength(code)} source bytes.`);
