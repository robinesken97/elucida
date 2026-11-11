// Synthetic fixture: two reaction rows and a stoichiometry table.
import fs from 'node:fs';
import {readOct, writeOct} from '../frontend/octet/src/oct.ts';
import {merge} from '../frontend/octet/src/edit.ts';
import {readStyle} from '../frontend/octet/src/docstyle.ts';
const p=process.argv[2]; const m=readOct(fs.readFileSync(p,'utf8')).mol;
const both=merge(m,m,[0,-18]);
both.captions ??=[];
both.captions.push({id:9999,x:0,y:-40,text:'NOT_FOR_SI'});
both.grids=[{arrow:m.arrows[0].id,typed:{r0:{moles:.005},'r:"K2CO3"':{density:2.43}},limiting:'r0'}];
fs.writeFileSync(p,writeOct(both,readStyle(m.style)));
