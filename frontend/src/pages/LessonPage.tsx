import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft, ArrowRight, BookOpen, CheckCircle2, Circle, Lightbulb,
  ListChecks, RotateCcw, Target, TriangleAlert
} from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { useApp, type Course, type CourseLesson, type CourseModule } from '../context/AppContext';

type LessonSection = {
  type: 'paragraph' | 'bullets' | 'steps' | 'definition' | 'callout' | 'table';
  title?: string;
  body?: string;
  items?: string[];
  rows?: string[][];
  tone?: 'important' | 'exam' | 'key';
};

function domainFor(course: Course): string {
  const text = `${course.name} ${course.category} ${course.specialization || ''}`.toLowerCase();
  if (/network|telecom|wireless|routing|protocol|security/.test(text)) return 'networking';
  if (/program|software|algorithm|computer science|information technology|web|mobile|devops|compiler/.test(text)) return 'computing';
  if (/database|data science|analytics|statistics|mathematics|math/.test(text)) return 'data';
  if (/artificial intelligence|machine learning|deep learning|neural|robot/.test(text)) return 'ai';
  if (/business|commerce|management|finance|marketing|account|econom|human resource|entrepreneur/.test(text)) return 'business';
  if (/electrical|electronics|instrument|power|circuit|control|telecom/.test(text)) return 'engineering';
  if (/medical|medicine|clinical|nursing|pharmacy|neurology|radiology|biomedical|psychology/.test(text)) return 'health';
  return 'general';
}

function buildLessonSections(course: Course, module: CourseModule, lesson: CourseLesson): LessonSection[] {
  const domain = domainFor(course);
  const topic = module.title || lesson.title.replace(/\s*:\s*Core Learning\s*$/i, '').trim();
  const coverage = module.coverage || module.content || `Core concepts and applications of ${topic}.`;
  const courseName = course.name;

  const domainLens: Record<string, { definition: string; example: string; process: string; comparison: string }> = {
    networking: {
      definition: `${topic} is a study area within ${courseName} concerned with how connected systems communicate, exchange information, and apply rules that make communication predictable and useful.`,
      example: `Consider a student opening a web application. The user sees one action, but the underlying system may involve addressing, packet forwarding, transport behavior, application protocols, error handling, and security controls. Studying ${topic} means being able to identify the role of each layer or mechanism rather than treating the network as one black box.`,
      process: `A useful way to analyze a networking mechanism is to identify the sender and receiver, the data being exchanged, the rules governing the exchange, the state maintained by each side, and what happens when packets are delayed, duplicated, corrupted, or lost.`,
      comparison: `When comparing two networking approaches, focus on connection model, reliability, ordering, overhead, control mechanisms, scalability, and the application requirements they are intended to satisfy.`
    },
    computing: {
      definition: `${topic} is a structured area of ${courseName} that explains concepts, representations, procedures, and design decisions used to build or reason about computing systems.`,
      example: `A practical study example is a small software feature: first identify the required input and output, then choose an appropriate representation, apply the relevant procedure or algorithm, test normal cases, and finally examine edge cases and failure conditions. This turns an abstract definition into an observable engineering decision.`,
      process: `A strong computing workflow is: define the problem, state assumptions, identify inputs and outputs, choose a representation, apply the algorithm or design, test representative cases, analyze complexity or trade-offs, and document limitations.`,
      comparison: `For competing computing techniques, compare correctness, time and space requirements, maintainability, implementation complexity, scalability, and suitability for the actual workload rather than declaring one method universally superior.`
    },
    data: {
      definition: `${topic} is a study area in ${courseName} concerned with representing, organizing, analyzing, or interpreting information so that conclusions can be made from clearly stated assumptions.`,
      example: `Suppose a dataset contains observations from several groups. A sound analysis first identifies the variables and their meaning, checks data quality, selects an appropriate representation or method, performs the calculation or transformation, and then interprets the result in context. A numerical output without interpretation is not a complete analysis.`,
      process: `A reliable analytical workflow is: define the question, identify variables, inspect the data, state assumptions, choose the method, compute or transform step by step, validate the result, and explain what the result does and does not establish.`,
      comparison: `When comparing analytical methods, examine assumptions, input requirements, sensitivity to noise or outliers, interpretability, computational cost, and the kind of conclusion each method supports.`
    },
    ai: {
      definition: `${topic} is a component of ${courseName} that focuses on methods for representing information, learning patterns, making decisions, or constructing systems that perform tasks normally requiring substantial human reasoning.`,
      example: `Consider a model used to classify new observations. The workflow is not simply "train a model": the practitioner defines the target, prepares data, chooses features or representations, selects a method, trains it, evaluates it on appropriate data, checks failure cases, and interprets whether the measured performance supports the intended use.`,
      process: `A useful AI/ML workflow is: define the task, establish the data and target, prepare representations, choose a model or algorithm, train or compute, evaluate with suitable metrics, inspect errors, and document assumptions and limitations.`,
      comparison: `Compare AI methods using task suitability, data requirements, assumptions, interpretability, computational cost, robustness, and evaluation methodology. A method should be judged against the problem and evidence, not by its name alone.`
    },
    business: {
      definition: `${topic} is a structured area of ${courseName} that explains how people, resources, incentives, information, and decisions interact within an organization or market.`,
      example: `A realistic case can be analyzed by separating facts from assumptions, identifying stakeholders, defining the objective, comparing available alternatives, estimating consequences, and stating risks. This approach prevents a business answer from becoming a list of disconnected terms.`,
      process: `A useful business-analysis workflow is: define the decision, identify stakeholders and constraints, collect relevant evidence, identify alternatives, compare costs and benefits, consider risks and implementation, and state measurable outcomes.`,
      comparison: `When comparing business approaches, consider objective, resources, incentives, time horizon, risk, implementation difficulty, stakeholder effects, and measurable outcomes.`
    },
    engineering: {
      definition: `${topic} is an engineering study area in ${courseName} concerned with understanding a system, its components, governing principles, operating conditions, and the trade-offs involved in designing or analyzing it.`,
      example: `An engineering problem can be approached by defining the system boundary, identifying known quantities and constraints, selecting the governing principle or model, solving step by step, checking units and boundary conditions, and interpreting the result in physical or operational terms.`,
      process: `A reliable engineering workflow is: define the system, list known and unknown quantities, state assumptions, select the governing model, solve or design step by step, verify units and limits, then interpret the result and identify failure conditions.`,
      comparison: `Engineering alternatives should be compared using performance, safety, reliability, efficiency, cost, complexity, maintainability, operating conditions, and the constraints of the application.`
    },
    health: {
      definition: `${topic} is a structured academic area within ${courseName} that organizes concepts, mechanisms, terminology, observations, and evidence relevant to understanding a health-related system or practice.`,
      example: `A sound academic analysis begins by defining the relevant concept, distinguishing normal from abnormal patterns where the source supports that distinction, identifying mechanisms or contributing factors, and then interpreting an example without confusing a study framework with an individual clinical decision.`,
      process: `A useful learning workflow is: define the term, establish the mechanism or framework, identify relevant factors, connect the concept to an example, compare related concepts, review limitations, and finish with an exam-ready summary.`,
      comparison: `Compare related concepts by definition, mechanism, characteristic findings or properties, typical context, limitations, and the evidence or assumptions used to distinguish them.`
    },
    general: {
      definition: `${topic} is a focused study area within ${courseName}. It can be understood by separating its terminology, underlying ideas, process or framework, examples, applications, limitations, and relationships to nearby concepts.`,
      example: `A useful way to make the topic concrete is to start with a realistic scenario, identify which concepts are involved, explain the sequence of reasoning or action, and then check what would change if an assumption or input were different.`,
      process: `A reliable study workflow is: define the problem or concept, identify the important terms, state assumptions, explain the mechanism or framework step by step, apply it to an example, compare related ideas, and review limitations.`,
      comparison: `When two approaches or concepts are related, compare their definitions, purpose, assumptions, mechanism, strengths, limitations, and appropriate use rather than relying on a single memorized difference.`
    }
  };

  const lens = domainLens[domain];
  const objectives = [
    `Explain the meaning and scope of ${topic} in the context of ${courseName}.`,
    `Identify the important terms, components, assumptions, and relationships described by this lesson.`,
    `Apply the lesson framework to a concrete example or problem.`,
    `Compare related ideas and explain the trade-offs or limitations that matter.`,
    `Produce a concise exam-ready explanation using definitions, steps, examples, and key takeaways.`
  ];

  const coreParagraph = `The module coverage supplied for this course is "${coverage}". Use that coverage as the boundary of this lesson: the aim is not to memorize the heading alone, but to connect the heading to a coherent chain of ideas. Start with terminology, then ask what problem the concept addresses, what inputs or conditions it assumes, what mechanism or framework it uses, and what outcome it produces. Finally, ask when the approach is useful and what its limitations are. This sequence creates a mental model that is easier to retrieve during revision than isolated facts.`;

  const reasoningParagraph = `For exam preparation, explain ${topic} at three levels. At the first level, give a precise definition and identify the main components. At the second level, explain how those components interact and why the sequence or relationship matters. At the third level, apply the idea to a scenario and discuss what would change if an assumption, input, or constraint changed. This progression from definition to mechanism to application is especially useful for medium and hard questions because it requires understanding rather than recognition.`;

  const applicationParagraph = `When revising ${topic}, keep a distinction between the concept itself and the context in which it is applied. A definition tells you what something means; a model explains how it behaves; an example shows how the model is used; and a limitation tells you when the model should not be trusted without further evidence. Keeping these four layers separate makes it easier to answer questions that ask for comparisons, advantages and disadvantages, case analysis, or step-by-step reasoning.`;

  return [
    { type:'paragraph', title:'Introduction', body:`This lesson develops ${topic} as part of ${courseName}. The goal is to turn the supplied curriculum coverage into a studyable mental model: what the topic means, why it matters, how its parts fit together, how it is applied, and where its limits appear. ${lens.definition} The module blueprint identifies ${coverage.toLowerCase()}.` },
    { type:'bullets', title:'Learning Objectives', items:objectives },
    { type:'definition', title:`Definition — ${topic}`, body:lens.definition },
    { type:'paragraph', title:'Why This Topic Matters', body:`${coreParagraph} ${lens.example}` },
    { type:'paragraph', title:'Core Concepts', body:`${reasoningParagraph} ${applicationParagraph}` },
    { type:'steps', title:'A Practical Study / Analysis Workflow', items:[
      `Define ${topic} precisely and write the key terms in your own words.`,
      `Identify the main components, assumptions, inputs, outputs, or stakeholders relevant to the topic.`,
      `Explain the mechanism or framework in a logical order instead of listing disconnected facts.`,
      `Work through one representative example and state why each step is justified.`,
      `Test an edge case or changed assumption and explain what would happen.`,
      `Compare the approach with a closely related concept and identify the meaningful difference.`,
      `Summarize the result, limitations, and exam points in a short revision block.`
    ]},
    { type:'callout', title:'Important Concept', body:`A strong answer about ${topic} should connect definition → mechanism → example → limitation. Memorizing only the definition is usually not enough for application or reasoning questions.`, tone:'important' },
    { type:'paragraph', title:'Worked Example / Scenario', body:`Imagine a realistic scenario in which ${topic} must be understood or applied. First identify the objective and the facts that are actually known. Next select the relevant concept from the lesson rather than introducing an unrelated method. Apply the mechanism in a clear sequence, state any assumption you are making, and then interpret the result. ${lens.example} If the scenario changes, repeat the same reasoning rather than memorizing a second answer. This is the transferable skill the lesson is intended to build.` },
    { type:'table', title:'How to Compare Related Concepts', rows:[
      ['Dimension','Question to ask while revising'],
      ['Purpose','What problem is each concept designed to address?'],
      ['Mechanism','How does each approach work or produce its outcome?'],
      ['Assumptions','What must be true for the approach to be appropriate?'],
      ['Strengths','What does the approach handle particularly well?'],
      ['Limitations','Where can it fail, become inefficient, or require additional evidence?'],
      ['Application','What kind of scenario makes the approach appropriate?']
    ]},
    { type:'paragraph', title:'Applications and Limitations', body:`${lens.process} ${lens.comparison} The important point is that an academically strong explanation does not stop at "how it works." It also identifies the conditions under which the method is appropriate and the evidence needed to support the conclusion. In practical work, document assumptions and test boundary cases. In an exam, state the assumption before applying a formula, algorithm, framework, or classification rule.` },
    { type:'bullets', title:'Common Mistakes', items:[
      `Giving a definition of ${topic} without explaining its purpose or mechanism.`,
      `Memorizing a list of terms without understanding how the terms relate.`,
      `Applying a familiar method without checking whether its assumptions fit the problem.`,
      `Confusing an example with the definition of the concept.`,
      `Ignoring edge cases, limitations, or the conditions stated in the question.`,
      `Writing a conclusion without explaining the reasoning that leads to it.`
    ]},
    { type:'callout', title:'Exam Tip', body:`For a long-answer question on ${topic}, use a predictable structure: definition → purpose → components → mechanism/steps → example → comparison or limitation → conclusion. This makes the answer easy to follow and helps you cover the points examiners commonly look for.`, tone:'exam' },
    { type:'bullets', title:'Key Takeaways', items:[
      `${topic} should be understood as a connected framework, not as an isolated heading.`,
      `Definitions establish meaning; mechanisms explain relationships; examples show application.`,
      `Assumptions and limitations are part of correct understanding.`,
      `Comparison questions should focus on purpose, mechanism, assumptions, strengths, and limitations.`,
      `A good revision answer can move from concept to application without changing the underlying reasoning.`
    ]},
    { type:'paragraph', title:'Quick Revision', body:`${topic} → define it → identify its components → explain the mechanism → apply it to an example → check assumptions → compare related concepts → remember limitations → finish with the key takeaway.` }
  ];
}

function wordCount(sections: LessonSection[]) {
  return sections.reduce((n, s) => {
    const text = [s.title, s.body, ...(s.items || []), ...((s.rows || []).flat())].filter(Boolean).join(' ');
    return n + text.trim().split(/\s+/).filter(Boolean).length;
  }, 0);
}

export default function LessonPage() {
  const { courseId, lessonId } = useParams();
  const navigate = useNavigate();
  const { courses, courseProgress, markCourseLesson, setLastCourseLesson } = useApp();
  const base = courses.find(c => c.id === courseId);
  const [course, setCourse] = useState<Course | undefined>(base);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!courseId) return;
    let cancelled = false;
    fetch(`/data/courses/${encodeURIComponent(courseId)}.json`)
      .then(r => r.ok ? r.json() : Promise.reject(new Error('Course unavailable')))
      .then((data: Course) => { if (!cancelled) { setCourse(data); setLoading(false); } })
      .catch(() => { if (!cancelled) { setCourse(base); setLoading(false); } });
    return () => { cancelled = true; };
  }, [courseId, base]);

  const modules = course?.modules || [];
  const flatLessons = useMemo(() => modules.flatMap(m => m.lessons.map(l => ({ module: m, lesson: l }))), [modules]);
  const index = flatLessons.findIndex(x => x.lesson.id === lessonId);
  const current = index >= 0 ? flatLessons[index] : undefined;
  const progress = courseId ? (courseProgress[courseId] || { completedLessonIds: [], completedQuizIds: [] }) : { completedLessonIds: [], completedQuizIds: [] };
  const completed = new Set(progress.completedLessonIds || []);

  if (loading) return <div className="page-stack"><div className="content-card">Loading lesson…</div></div>;
  if (!course || !current) return <div className="page-stack"><div className="empty-state"><h3>Lesson not found</h3><button className="btn secondary" onClick={() => navigate(`/courses/${courseId || ''}`)}><ArrowLeft size={15}/>Back to Course</button></div></div>;

  const { module, lesson } = current;
  const sections = buildLessonSections(course, module, lesson);
  const words = wordCount(sections);
  const done = completed.has(lesson.id);
  const previous = flatLessons[index - 1];
  const next = flatLessons[index + 1];

  const goTo = (target?: { module: CourseModule; lesson: CourseLesson }) => {
    if (!target || !courseId) return;
    setLastCourseLesson(courseId, target.lesson.id);
    navigate(`/courses/${courseId}/lessons/${target.lesson.id}`);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const toggleComplete = () => {
    if (!courseId) return;
    markCourseLesson(courseId, lesson.id, !done);
  };

  return <div className="page-stack lesson-page">
    <div className="page-hero lesson-hero">
      <div>
        <button className="link-btn" onClick={() => navigate(`/courses/${course.id}`)}><ArrowLeft size={15}/>Back to Course</button>
        <div className="eyebrow">{course.name} · MODULE {module.number || index + 1}</div>
        <h1>{course.topics[Math.max(0, (module.number || 1) - 1)] || lesson.title.replace(/\s*:\s*Core Learning\s*$/i, '')}</h1>
        <p>{lesson.description || module.coverage || `Structured lesson for ${course.name}.`}</p>
        <div className="lesson-meta-row">
          <span><BookOpen size={14}/> {words.toLocaleString()} words</span>
          <span><Target size={14}/> Focused study lesson</span>
          <span>{done ? <><CheckCircle2 size={14}/> Completed</> : <><Circle size={14}/> In progress</>}</span>
        </div>
      </div>
    </div>

    <div className="lesson-progress-card content-card">
      <div className="flex justify-between gap-4 items-center">
        <div><div className="section-kicker">YOUR COURSE PROGRESS</div><strong>{Math.round(((completed.size) / Math.max(1, flatLessons.length)) * 100)}% of lessons completed</strong></div>
        <button className={`btn ${done ? 'secondary' : 'primary'}`} onClick={toggleComplete}>
          {done ? <><RotateCcw size={15}/>Mark Incomplete</> : <><CheckCircle2 size={15}/>Mark Complete</>}
        </button>
      </div>
      <div className="progress-track large"><span style={{width:`${Math.min(100, Math.round(completed.size/Math.max(1,flatLessons.length)*100))}%`}}/></div>
    </div>

    <article className="lesson-document">
      {sections.map((section, i) => {
        if (section.type === 'definition') return <section className="lesson-section" key={i}><h2>{section.title}</h2><div className="definition-card"><div className="section-kicker">DEFINITION</div><p>{section.body}</p></div></section>;
        if (section.type === 'callout') return <section className="lesson-section" key={i}><div className={`lesson-callout ${section.tone || 'important'}`}><Lightbulb size={19}/><div><h3>{section.title}</h3><p>{section.body}</p></div></div></section>;
        if (section.type === 'bullets') return <section className="lesson-section" key={i}><h2>{section.title}</h2><ul className="lesson-bullets">{section.items?.map((x,j)=><li key={j}>{x}</li>)}</ul></section>;
        if (section.type === 'steps') return <section className="lesson-section" key={i}><h2>{section.title}</h2><ol className="lesson-steps">{section.items?.map((x,j)=><li key={j}><span>{j+1}</span><p>{x}</p></li>)}</ol></section>;
        if (section.type === 'table') return <section className="lesson-section" key={i}><h2>{section.title}</h2><div className="lesson-table-wrap"><table className="lesson-table"><tbody>{section.rows?.map((row,j)=><tr key={j}>{row.map((cell,k)=>j===0?<th key={k}>{cell}</th>:<td key={k}>{cell}</td>)}</tr>)}</tbody></table></div></section>;
        return <section className="lesson-section" key={i}><h2>{section.title}</h2><p>{section.body}</p></section>;
      })}
    </article>

    <div className="lesson-nav content-card">
      <button className="btn secondary" disabled={!previous} onClick={() => goTo(previous)}><ArrowLeft size={15}/>Previous Lesson</button>
      <div className="lesson-nav-center"><ListChecks size={16}/><span>{index + 1} of {flatLessons.length}</span></div>
      <button className="btn primary" disabled={!next} onClick={() => goTo(next)}>Next Lesson<ArrowRight size={15}/></button>
    </div>

    <div className="content-card lesson-practice-card">
      <div className="section-kicker">REVIEW CHECK</div>
      <h2>Before you leave this lesson</h2>
      <p>Can you define the topic, explain the main mechanism, apply it to an example, and state at least one limitation? If not, revisit the sections above before taking the module assessment.</p>
      <div className="flex flex-wrap gap-2">
        <span className="soft-badge">Definition</span><span className="soft-badge">Mechanism</span><span className="soft-badge">Example</span><span className="soft-badge">Limitations</span>
      </div>
    </div>

    <div className="text-xs muted flex items-center gap-2"><TriangleAlert size={14}/>This lesson is generated from the course's local academic blueprint and course metadata. For source-grounded academic claims, use verified lecture notes/textbooks in Knowledge.</div>
  </div>;
}
