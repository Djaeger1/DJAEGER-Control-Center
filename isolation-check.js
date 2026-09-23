'use strict';
const fs=require('fs'),path=require('path');
const pairs=[['DJAEGER','WORK'],['HERMES','WORK'],['railway','relay'],['AUTO','STUDIO'],['YOUTUBE','SCHEDULER'],['studio','feed']];
const forbidden=[];for(const [a,b] of pairs){for(const sep of ['-','_',' '])forbidden.push((a+sep+b).toLowerCase());}
const hits=[];
function walk(p){for(const e of fs.readdirSync(p,{withFileTypes:true})){if(e.name==='.git'||e.name==='node_modules')continue;const f=path.join(p,e.name);if(e.isDirectory())walk(f);else{let s='';try{s=fs.readFileSync(f,'utf8').toLowerCase();}catch{continue;}for(const q of forbidden)if(s.includes(q))hits.push(path.relative(process.cwd(),f)+':'+q);}}}
const sourceRoot=path.join(process.cwd(),'observer-next');walk(sourceRoot);if(hits.length){console.error('FAIL|FOREIGN_PROJECT_RESIDUE|'+hits.join(','));process.exit(1);}console.log('PASS|DJAEGER_AI_SOURCE_ISOLATION');
