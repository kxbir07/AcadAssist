import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
const dir=path.resolve(here,'../public/data/courses');
const errors=[]; const stats={courses:0,modules:0,lessons:0,moduleQuizzes:0,finalQuizzes:0,shortSourceLessons:0};
for(const file of fs.readdirSync(dir).filter(x=>x.endsWith('.json')).sort()){
  const c=JSON.parse(fs.readFileSync(path.join(dir,file),'utf8')); stats.courses++;
  if(!c.id||!c.name||!c.description) errors.push(`${file}: missing course metadata`);
  const modules=Array.isArray(c.modules)?c.modules:[]; stats.modules+=modules.length; if(!modules.length) errors.push(`${c.id}: no modules`);
  const mids=new Set(), lids=new Set(), seen=new Set();
  for(const m of modules){ if(!m.id||mids.has(m.id)) errors.push(`${c.id}: duplicate/missing module id`); mids.add(m.id); const lessons=Array.isArray(m.lessons)?m.lessons:[]; if(!lessons.length) errors.push(`${c.id}/${m.id}: no lessons`); for(const l of lessons){stats.lessons++; if(!l.id||lids.has(l.id)) errors.push(`${c.id}: duplicate/missing lesson id`); lids.add(l.id); const words=String(l.content||'').trim().split(/\\s+/).filter(Boolean).length; if(words<20) stats.shortSourceLessons++;}}
  const mqs=Array.isArray(c.moduleQuizzes)?c.moduleQuizzes:[]; stats.moduleQuizzes+=mqs.length; if(mqs.length!==modules.length) errors.push(`${c.id}: module quiz count mismatch`);
  for(const qz of mqs){const qs=Array.isArray(qz.questions)?qz.questions:[]; if(qs.length<12) errors.push(`${c.id}/${qz.id}: fewer than 12 questions`); for(const q of qs){const k=String(q.question||'').trim().toLowerCase(); if(seen.has(k)) errors.push(`${c.id}: duplicate question`); seen.add(k); if(!Array.isArray(q.options)||q.options.length<4||!Number.isInteger(q.correctIndex)||q.correctIndex<0||q.correctIndex>=q.options.length) errors.push(`${c.id}/${qz.id}: invalid question`);}}
  const fq=c.finalQuiz||c.quiz; if(!fq) errors.push(`${c.id}: missing final quiz`); else {stats.finalQuizzes++; const qs=Array.isArray(fq.questions)?fq.questions:[]; if(qs.length<25||qs.length>35) errors.push(`${c.id}: final quiz must contain 25-35 questions`); for(const q of qs){const k=String(q.question||'').trim().toLowerCase(); if(seen.has(k)) errors.push(`${c.id}: final quiz duplicates module question`); seen.add(k); if(!Array.isArray(q.options)||q.options.length<4||!Number.isInteger(q.correctIndex)||q.correctIndex<0||q.correctIndex>=q.options.length) errors.push(`${c.id}: invalid final question`);}}
}
console.log(JSON.stringify({...stats,renderedLessonContent:'LessonPage builds structured local long-form content from the course/module blueprint when stored lesson text is compact.',errors},null,2));
if(errors.length) process.exit(1);
