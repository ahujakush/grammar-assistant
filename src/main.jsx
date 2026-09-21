import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BookOpen, BrainCircuit, Check, ChevronRight, CircleAlert, Code2, Compass, Copy, Download, Link2, LoaderCircle, Moon, Play, RotateCcw, Sparkles, Sun, WandSparkles } from 'lucide-react'
import AutomatonDiagram, { simulateAutomaton, tokenizeInput } from './AutomatonDiagram'
import GrammarGuide from './GrammarGuide'
import './styles.css'

const API_URL = import.meta.env.VITE_API_URL || ''

function inferStartSymbol(grammarText) {
  const firstProduction = grammarText.split(/\r?\n/).find(line => line.includes('->') || line.includes('→'))
  return firstProduction?.split(/->|→/, 1)[0].trim().split(/\s+/)[0] || ''
}

async function apiRequest(path, options) {
  const response = await fetch(`${API_URL}${path}`, options)
  if (!API_URL && (response.status === 404 || response.status === 405)) {
    return fetch(`http://localhost:8000${path}`, options)
  }
  return response
}

const demos = {
  Regular: { text: 'S -> aA | b\nA -> aS | a', start: 'S' },
  CFG: { text: 'S -> aSb | ε', start: 'S' },
  'Left recursive': { text: 'E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id', start: 'E' },
  'Context-sensitive': { text: 'S -> aSBC\nCB -> BC', start: 'S' },
  Unrestricted: { text: 'AB -> BA', start: 'A' }
}

function App() {
  const [grammar, setGrammar] = useState(demos.CFG.text)
  const [startSymbol, setStartSymbol] = useState(demos.CFG.start)
  const [result, setResult] = useState(null)
  const [activeDemo, setActiveDemo] = useState('CFG')
  const [loading, setLoading] = useState(false)
  const [question, setQuestion] = useState('Why is this grammar classified this way?')
  const [answer, setAnswer] = useState('')
  const [assistantLoading, setAssistantLoading] = useState(false)
  const [error, setError] = useState('')
  const [darkMode, setDarkMode] = useState(() => {
    const saved = window.localStorage.getItem('grammar-theme')
    return saved ? saved === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches
  })
  const [resultTab, setResultTab] = useState('overview')
  const [parseString, setParseString] = useState('')
  const [parseResult, setParseResult] = useState(null)
  const [parseLoading, setParseLoading] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [automatonMode, setAutomatonMode] = useState('nfa')
  const [automatonTest, setAutomatonTest] = useState('')
  const [automatonResult, setAutomatonResult] = useState(null)
  const [copyLabel, setCopyLabel] = useState('')
  const [currentView, setCurrentView] = useState('assistant')

  useEffect(() => {
    const readHash = () => {
      try {
        const params = new URLSearchParams(window.location.hash.replace(/^#/, ''))
        const sharedGrammar = params.get('grammar')
        const sharedStart = params.get('start')
        if (sharedGrammar !== null) {
          const nextStart = sharedStart || sharedGrammar.match(/^[A-Za-z][A-Za-z0-9_']*/)?.[0] || ''
          setGrammar(sharedGrammar); setStartSymbol(nextStart); analyze(sharedGrammar, nextStart)
        } else analyze()
      } catch { setError('The share link could not be read.') }
    }
    readHash()
    window.addEventListener('hashchange', readHash)
    return () => window.removeEventListener('hashchange', readHash)
  }, [])
  useEffect(() => {
    const theme = darkMode ? 'dark' : 'light'
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem('grammar-theme', theme)
  }, [darkMode])
  useEffect(() => {
    setStartSymbol(inferStartSymbol(grammar))
  }, [grammar])
  useEffect(() => {
    const handleShortcut = event => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); analyze() }
    }
    window.addEventListener('keydown', handleShortcut)
    return () => window.removeEventListener('keydown', handleShortcut)
  }, [grammar, startSymbol])

  async function analyze(grammarText = grammar, start = startSymbol) {
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const response = await apiRequest('/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ grammar: grammarText, start_symbol: start }) })
      if (!response.ok) throw new Error(`Analysis request failed with status ${response.status}`)
      const data = await response.json()
      setResult(data)
      setAnswer(data.explanation)
    } catch (error) {
      setError(`The backend is not reachable. Start FastAPI with uvicorn backend.main:app --reload --port 8000. ${error.message}`)
    } finally { setLoading(false) }
  }

  function loadDemo(name) {
    const demo = demos[name]
    setActiveDemo(name); setGrammar(demo.text); setStartSymbol(demo.start); setResultTab('overview'); setParseResult(null); setStepIndex(0); setAutomatonMode('nfa'); setAutomatonResult(null); setAnswer('Analyze a grammar to unlock a grounded explanation.'); analyze(demo.text, demo.start)
  }

  function loadGuideExample(exampleGrammar, exampleStart) {
    setGrammar(exampleGrammar)
    setStartSymbol(exampleStart)
    setActiveDemo('')
    setResult(null)
    setResultTab('overview')
    setParseResult(null)
    setStepIndex(0)
    setAutomatonMode('nfa')
    setAutomatonResult(null)
    setQuestion('')
    setAnswer('')
    setError('')
    setCurrentView('assistant')
  }

  async function parseStringInput() {
    setParseLoading(true)
    try {
      const response = await apiRequest('/api/parse', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ grammar, string: parseString, start_symbol: startSymbol }) })
      if (!response.ok) throw new Error(`Parse request failed with status ${response.status}`)
      const data = await response.json()
      setParseResult(data)
    } catch (requestError) { setError(requestError.message) } finally { setParseLoading(false) }
  }

  function showCopied(label) {
    setCopyLabel(label)
    window.setTimeout(() => setCopyLabel(''), 1500)
  }

  async function copyText(content, label) {
    try {
      if (!navigator.clipboard) return
      await navigator.clipboard.writeText(content)
      showCopied(label)
    } catch { setError('Copy is unavailable in this browser.') }
  }

  function copyLatex() {
    const content = result?.productions.map(rule => `\\text{${rule.replace('→', '\\to')}}`).join(' \\\\ ') || ''
    copyText(`\\begin{aligned}${content}\\end{aligned}`, 'LaTeX copied')
  }

  function downloadJson() {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
    const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'grammar-analysis.json'; link.click(); URL.revokeObjectURL(link.href)
  }

  async function copyShareLink() {
    const hash = `#grammar=${encodeURIComponent(grammar)}&start=${encodeURIComponent(startSymbol)}`
    const url = `${window.location.origin}${window.location.pathname}${hash}`
    window.history.replaceState(null, '', hash)
    await copyText(url, 'Share link copied')
  }

  function testAutomaton() {
    const tokens = tokenizeInput(automatonTest, result?.terminals || [])
    if (tokens?.error) { setAutomatonResult({ error: tokens.error }); return }
    setAutomatonResult(simulateAutomaton(automatonMode === 'dfa' && result.dfa ? result.dfa : result.automaton, tokens))
  }

  function jumpToStep(title) {
    const index = result?.steps?.findIndex(step => step.title === title) ?? -1
    if (index < 0) return
    setStepIndex(index)
    document.querySelector('.steps-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  async function explain() {
    if (!result || !question.trim()) return
    setAssistantLoading(true)
    setError('')
    try {
      const response = await apiRequest('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ grammar, question, start_symbol: startSymbol, parse_string: parseString }) })
      if (!response.ok) throw new Error(`Assistant request failed with status ${response.status}`)
      const data = await response.json()
      setAnswer(data.answer)
    } catch (requestError) { setAnswer(''); setError(requestError.message) } finally { setAssistantLoading(false) }
  }

  function clearChat() {
    setQuestion('')
    setAnswer('')
    setAssistantLoading(false)
    setError('')
  }

  const classification = result?.classification
  return <div className="app-shell" data-theme={darkMode ? 'dark' : 'light'}>
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><Compass size={21} /></div><div><p className="eyebrow">FORMAL SYSTEMS LAB / 01</p><h1>GrammarGenie</h1></div></div>
      <div className="topbar-meta"><span className="status-dot" /> Engine online <span className="version">v1.0 · local</span><nav className="view-nav" aria-label="Application views"><button className={currentView === 'assistant' ? 'active' : ''} onClick={() => setCurrentView('assistant')}>Grammar Assistant</button><button className={currentView === 'guide' ? 'active' : ''} onClick={() => setCurrentView('guide')}><BookOpen size={15} /> Grammar Guide</button></nav><button className="theme-button" onClick={() => setDarkMode(value => !value)} aria-label="Toggle Blueprint and Notebook theme">{darkMode ? <Sun size={15} /> : <Moon size={15} />} {darkMode ? 'NOTEBOOK' : 'BLUEPRINT'}</button></div>
    </header>
    {currentView === 'guide' ? <GrammarGuide onBack={() => setCurrentView('assistant')} onTryGrammar={loadGuideExample} currentGrammar={grammar} /> : <>
    <main className="workspace">
      <aside className="panel input-panel">
        <div className="panel-heading"><div><p className="eyebrow">01 / INPUT</p><h2>Grammar editor</h2></div><Code2 size={19} /></div>
        <div className="demo-block demo-top"><div className="field-label"><span>Demo grammars</span><Sparkles size={14} /></div><div className="demo-list">{Object.keys(demos).map(name => <button className={activeDemo === name ? 'demo-chip selected' : 'demo-chip'} key={name} onClick={() => loadDemo(name)}>{name}<ChevronRight size={13} /></button>)}</div></div>
        <div className="field-label"><span>Production rules</span><span className="format-hint">A → α</span></div>
        <textarea value={grammar} onChange={e => setGrammar(e.target.value)} spellCheck="false" aria-label="Grammar production rules" />
        <label className="field-label" htmlFor="start">Start symbol</label>
        <input id="start" value={startSymbol} readOnly aria-readonly="true" />
        <button className="primary-button" onClick={() => analyze()} disabled={loading}>{loading ? <LoaderCircle className="spin" size={17} /> : <Play size={16} />} Analyze grammar <ChevronRight size={16} /></button>
        <button className="ghost-button" onClick={() => { setGrammar(''); setResult(null) }}><RotateCcw size={15} /> Clear editor</button>
        <div className="input-note"><BookOpen size={15} /><span>Use <strong>ε</strong> or <strong>epsilon</strong> for the empty string. Alternatives use <strong>|</strong>. Adjacent lowercase letters form one terminal; spaces separate terminals.</span></div>
      </aside>

      <section className="analysis-column">
        <div className="section-intro"><div><p className="eyebrow">02 / ANALYSIS</p><h2>What does this grammar say?</h2><p className="muted">A deterministic reading of your productions, with the reasoning kept visible.</p></div><div className="hierarchy-strip"><span>T0</span><span>T1</span><span className={classification?.code === 2 ? 'active' : ''}>T2</span><span className={classification?.code === 3 ? 'active' : ''}>T3</span></div></div>
        {error && <div className="error-banner"><CircleAlert size={16} /><span>{error}</span></div>}
        {result ? <>
          <div className="classification-card"><div className="classification-label"><span className="signal" /> DETECTED HIERARCHY TYPE</div><div className="classification-main"><div><h3>{classification.label || classification.type}</h3><p>{classification.type} <span className="arrow">→</span> {classification.type === 'Type 3' ? 'Finite Automaton' : classification.type === 'Type 2' ? 'Pushdown Automaton' : classification.type === 'Type 1' ? 'Linear Bounded Automaton' : 'Turing Machine'}</p></div><div className="type-stamp">{classification.type.replace('Type ', 'T')}</div></div><div className="reason"><span>WHY</span><p>{classification.reason}</p></div></div>
          <div className="metrics-row"><Metric label="Non-terminals" value={result.non_terminals.join(', ') || '—'} /><Metric label="Terminals" value={result.terminals.join(' ') || '—'} /><Metric label="Productions" value={result.properties.production_count} /><Metric label="Start symbol" value={result.start_symbol || '—'} /></div>
          <div className="result-tabs"><button className={resultTab === 'overview' ? 'active' : ''} onClick={() => setResultTab('overview')}>Overview</button><button className={resultTab === 'first-follow' ? 'active' : ''} onClick={() => setResultTab('first-follow')}>FIRST / FOLLOW</button><button className={resultTab === 'll1' ? 'active' : ''} onClick={() => setResultTab('ll1')}>LL(1) table</button>{classification.code === 2 && <button className={resultTab === 'parse' ? 'active' : ''} onClick={() => setResultTab('parse')}>Parse tree</button>}</div>
          {resultTab === 'overview' && <div className="content-block"><div className="block-heading"><h3>Production analysis</h3><span>{result.valid ? 'VALIDATED' : 'NEEDS ATTENTION'}</span></div><div className="production-list">{result.productions.map((line, i) => <div className="production-row" key={line}><span>0{i + 1}</span><code>{line}</code><Check size={15} className="check" /></div>)}</div></div>}
          {resultTab === 'first-follow' && <FirstFollow result={result} />}
          {resultTab === 'll1' && <Ll1Table result={result} />}
          {resultTab === 'parse' && <ParsePanel parseString={parseString} setParseString={setParseString} parseStringInput={parseStringInput} parseLoading={parseLoading} parseResult={parseResult} />}
          <div className="content-block"><div className="block-heading"><h3>Validation results</h3><span>{result.validation.length} signals</span></div>{result.validation.length ? <div className="issue-list">{result.validation.map((issue, i) => <div className={`issue ${issue.severity}`} key={i}><CircleAlert size={15} /><span>{issue.message}</span></div>)}</div> : <div className="empty-state"><Check size={16} /> No validation issues detected.</div>}</div>
          {result.automaton && <AutomatonPanel result={result} mode={automatonMode} setMode={setAutomatonMode} automatonTest={automatonTest} setAutomatonTest={setAutomatonTest} automatonResult={automatonResult} testAutomaton={testAutomaton} />}
          {!result.automaton && result.classification.code === 2 && <button className="parse-tab-button" onClick={() => setResultTab('parse')}>Open parse tree tab</button>}
        </> : <div className="blank-analysis"><div className="blank-icon"><BrainCircuit size={30} /></div><h3>Ready when you are.</h3><p>Enter a grammar or load a demo, then run the analyzer to see its place in the Chomsky hierarchy.</p><div className="blank-rule" /></div>}
      </section>

      <aside className="panel transform-panel"><div className="panel-heading"><div><p className="eyebrow">03 / TRANSFORM</p><h2>Available moves</h2></div><WandSparkles size={19} /></div><p className="muted small">Operations appear here with their mathematical reason, not just a final answer.</p><div className="transform-list">{[
        ['Remove ε-productions', 'Remove epsilon-productions'],
        ['Remove unit productions', 'Remove unit productions'],
        ['Remove left recursion', 'Remove direct left recursion from E'],
        ['Left factoring', 'Left-factor S'],
        ['Convert to CNF', 'CNF: remove epsilon-productions']
      ].map(([item, title], i) => { const enabled = Boolean(result?.steps?.some(step => step.title === title)); return <button className="transform-item" key={item} disabled={!enabled} title={enabled ? '' : 'Not needed for this grammar'} onClick={() => jumpToStep(title)}><span className={enabled ? 'number active' : 'number'}>0{i + 1}</span><span>{item}</span><ChevronRight size={15} /></button> })}<button className="transform-item" disabled={!result?.automaton} title={result?.automaton ? '' : 'Not needed for this grammar'} onClick={() => document.querySelector('.automaton-graphic')?.scrollIntoView({ behavior: 'smooth', block: 'center' })}><span className={result?.automaton ? 'number active' : 'number'}>06</span><span>Grammar → NFA</span><ChevronRight size={15} /></button></div><div className="scope-card"><p className="eyebrow">SCOPE NOTE</p><p>Classification is rule-based. Explanations are generated from the same analysis object, so the assistant cannot silently change the mathematical result.</p></div></aside>
    </main>
    <section className="lower-grid"><div className="steps-section"><div className="lower-heading"><div><p className="eyebrow">04 / TRACE</p><h2>Transformation trace</h2></div><span className="muted small">Every generated intermediate state</span></div>{result?.steps?.length ? <StepViewer steps={result.steps} stepIndex={stepIndex} setStepIndex={setStepIndex} /> : <div className="trace-empty">Analyze a CFG with a transformation opportunity to see its trace.</div>}</div><div className="assistant-section"><div className="lower-heading"><div><p className="eyebrow">05 / EXPLAIN</p><h2>Grammar AI assistant</h2></div><BrainCircuit size={19} /></div>{answer ? <div className="assistant-chat"><div className="assistant-icon"><BrainCircuit size={18} /></div><p>{answer}</p></div> : <div className="assistant-empty"><strong>Ask a question about the current grammar.</strong><span>Example:</span><q>Why is this grammar classified as a CFG?</q></div>}<textarea className="assistant-question" value={question} onChange={e => setQuestion(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) explain() }} placeholder="Ask anything about this grammar..." aria-label="Ask a question about the grammar" /><div className="assistant-actions"><button className="secondary-button" onClick={explain} disabled={!result || !question.trim() || assistantLoading}>{assistantLoading ? <LoaderCircle className="spin" size={15} /> : <Sparkles size={15} />} Ask about current grammar</button><button className="secondary-button" onClick={clearChat} disabled={assistantLoading}><RotateCcw size={15} /> Clear Chat</button></div><div className="export-actions"><button onClick={copyLatex}><Copy size={14} /> Copy LaTeX</button><button onClick={downloadJson}><Download size={14} /> Download JSON</button><button onClick={copyShareLink}><Link2 size={14} /> Copy share link</button></div></div></section>
    <footer><span>GRAMMARGENIE</span><span>DETERMINISTIC ENGINE · ACADEMIC MODE</span></footer></>}
  </div>
}

function Metric({ label, value }) { return <div className="metric"><span>{label}</span><strong>{value}</strong></div> }

function AutomatonPanel({ result, mode, setMode, automatonTest, setAutomatonTest, automatonResult, testAutomaton }) {
  const automaton = mode === 'dfa' && result.dfa ? result.dfa : result.automaton
  const transitions = automaton.transitions || []
  return <div className="content-block"><div className="block-heading"><h3>Grammar → automaton</h3><div className="automaton-controls"><span>{automaton.states?.length || 0} states · regex {result.regex || '—'}</span>{result.dfa && <div className="mode-switch"><button className={mode === 'nfa' ? 'active' : ''} onClick={() => setMode('nfa')}>NFA</button><button className={mode === 'dfa' ? 'active' : ''} onClick={() => setMode('dfa')}>DFA</button></div>}</div></div><div className="automaton-graphic"><AutomatonDiagram automaton={automaton} active={automatonResult?.activeStates || []} /></div><div className="automaton-test"><input value={automatonTest} onChange={event => setAutomatonTest(event.target.value)} placeholder="Test a string, e.g. aaa" aria-label="Test automaton string" /><button className="secondary-button" onClick={testAutomaton}><Play size={14} /> Test string</button></div>{automatonResult && <div className={automatonResult.error || !automatonResult.accepted ? 'parse-result rejected' : 'parse-result accepted'}>{automatonResult.error || (automatonResult.accepted ? 'Accepted.' : 'Rejected.')}{automatonResult.states && <div className="automaton-states">{automatonResult.states.map((statesAtStep, index) => <div key={index}><code>{index === 0 ? 'start' : `after symbol ${index}`}</code> {statesAtStep.join(', ') || '∅'}</div>)}</div>}</div>}<details className="transition-details"><summary>Transition table</summary><div className="transition-table">{transitions.map((transition, index) => <div key={`${transition.from}-${transition.symbol}-${index}`}><code>{transition.from}</code><span>{transition.symbol}</span><code>{transition.to}</code></div>)}</div></details></div>
}

function LegacyAutomatonPanel({ result, mode, setMode, parseString, setParseString, parseStringInput, parseLoading, parseResult }) {
  const automaton = mode === 'dfa' && result.dfa ? result.dfa : result.automaton
  const states = automaton.states || []
  const transitions = automaton.transitions || []
  return <div className="content-block"><div className="block-heading"><h3>Grammar → automaton</h3><div className="automaton-controls"><span>{states.length} states · regex {result.regex || '—'}</span>{result.dfa && <div className="mode-switch"><button className={mode === 'nfa' ? 'active' : ''} onClick={() => setMode('nfa')}>NFA</button><button className={mode === 'dfa' ? 'active' : ''} onClick={() => setMode('dfa')}>DFA</button></div>}</div></div><div className="automaton-graphic"><svg viewBox="0 0 620 150" role="img" aria-label={`${mode.toUpperCase()} finite automaton state diagram`}><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="currentColor" /></marker></defs>{transitions.map((transition, index) => { const from = states.indexOf(transition.from); const to = states.indexOf(transition.to); const x1 = 70 + Math.max(from, 0) * 150; const x2 = 70 + Math.max(to, 0) * 150; return <g key={`${transition.from}-${transition.symbol}-${index}`}><line x1={x1} y1="75" x2={x2} y2="75" className="edge" markerEnd="url(#arrow)" /><text x={(x1 + x2) / 2} y="61" className="edge-label">{transition.symbol}</text></g>})}{states.map((state, index) => { const x = 70 + index * 150; const final = automaton.final_states?.includes(state); const start = automaton.start === state || automaton.start_state === state; return <g key={state}><circle cx={x} cy="75" r="28" className="state-node" />{final && <circle cx={x} cy="75" r="23" className="final-node" />}<text x={x} y="80" textAnchor="middle" className="state-label">{state}</text>{start && <line x1={x - 48} y1="75" x2={x - 28} y2="75" className="edge" markerEnd="url(#arrow)" />}</g>})}</svg></div><div className="automaton-test"><input value={parseString} onChange={event => setParseString(event.target.value)} placeholder="Test a string, e.g. aaa" aria-label="Test automaton string" /><button className="secondary-button" onClick={parseStringInput} disabled={parseLoading}>{parseLoading ? <LoaderCircle className="spin" size={14} /> : <Play size={14} />} Test string</button></div>{parseResult && <div className={parseResult.accepted ? 'parse-result accepted' : 'parse-result rejected'}>{parseResult.accepted ? 'Accepted by the grammar.' : 'Not accepted by the grammar.'}{(parseResult.tree || parseResult.parse_tree) && <ParseTree node={parseResult.tree || parseResult.parse_tree} />}</div>}</div>
}

function ParseTree({ node }) { return <div className="parse-tree"><div className="tree-node">{node.symbol}</div>{node.children?.length > 0 && <div className="tree-children">{node.children.map((child, index) => <ParseTree node={child} key={`${child.symbol}-${index}`} />)}</div>}</div> }

function ParsePanel({ parseString, setParseString, parseStringInput, parseLoading, parseResult }) {
  return <div className="content-block"><div className="block-heading"><h3>CYK parse test</h3><span>CONTEXT-FREE GRAMMAR</span></div><div className="automaton-test"><input value={parseString} onChange={event => setParseString(event.target.value)} placeholder="Test a string, e.g. a a b b" aria-label="Test grammar string" /><button className="secondary-button" onClick={parseStringInput} disabled={parseLoading}>{parseLoading ? <LoaderCircle className="spin" size={14} /> : <Play size={14} />} Parse string</button></div>{parseResult && <div className={parseResult.accepted ? 'parse-result accepted' : 'parse-result rejected'}>{parseResult.error || (parseResult.accepted ? 'Accepted by CYK.' : 'Rejected by CYK.')}{(parseResult.tree || parseResult.parse_tree) && <ParseTree node={parseResult.tree || parseResult.parse_tree} />}</div>}</div>
}

function StepViewer({ steps, stepIndex, setStepIndex }) {
  const step = steps[stepIndex]
  const added = step.added || step.grammar
  const removed = step.removed || []
  const retained = step.retained || []
  return <div className="stepper"><div className="stepper-nav">{steps.map((item, index) => <button className={index === stepIndex ? 'active' : ''} onClick={() => setStepIndex(index)} key={item.title}>{String(index + 1).padStart(2, '0')} {item.title}</button>)}</div><div className="step"><div className="step-index">{String(stepIndex + 1).padStart(2, '0')}</div><div className="step-body"><h3>{step.title}</h3><p>{step.explanation}</p><div className="diff-grid"><div><p className="set-title">ADDED</p>{(added.length ? added : ['No rules added']).map(line => <code className="diff-added" key={line}>+ {line}</code>)}</div><div><p className="set-title">REMOVED</p>{(removed.length ? removed : ['No rules removed']).map(line => <code className="diff-removed" key={line}>- {line}</code>)}</div><div><p className="set-title">RETAINED</p>{(retained.length ? retained : ['No rules retained']).map(line => <code className="diff-retained" key={line}>{line}</code>)}</div></div></div></div></div>
}

createRoot(document.getElementById('root')).render(<App />)
function FirstFollow({ result }) {
  const data = result.first_follow || { first: result.first, follow: result.follow }
  if (!data) return <div className="content-block"><div className="empty-state">FIRST/FOLLOW data is unavailable.</div></div>
  const nonTerminals = new Set(data.non_terminals || result.non_terminals || Object.keys(data.follow || {}))
  const firstEntries = Object.entries(data.first || {}).filter(([symbol]) => nonTerminals.has(symbol))
  const followEntries = Object.entries(data.follow || {}).filter(([symbol]) => nonTerminals.has(symbol))
  return <div className="content-block"><div className="block-heading"><h3>Predictive parsing sets</h3><span>DETERMINISTIC</span></div><div className="sets-grid"><div><p className="set-title">FIRST</p>{firstEntries.map(([symbol, values]) => <div className="set-row" key={`first-${symbol}`}><code>{symbol}</code><span>{values.join(', ') || '∅'}</span></div>)}</div><div><p className="set-title">FOLLOW</p>{followEntries.map(([symbol, values]) => <div className="set-row" key={`follow-${symbol}`}><code>{symbol}</code><span>{values.join(', ') || '∅'}</span></div>)}</div></div></div>
}

function Ll1Table({ result }) {
  const data = result.ll1
  if (!data) return <div className="content-block"><div className="empty-state">LL(1) data is unavailable.</div></div>
  const rows = Object.entries(data.table)
  return <div className="content-block"><div className="block-heading"><h3>LL(1) parsing table</h3><span>{data.is_ll1 ? 'NO CONFLICTS' : `${data.conflicts.length} CONFLICTS`}</span></div><p className="table-verdict">{data.is_ll1 ? 'This grammar is LL(1).' : `Not LL(1): ${data.conflicts.length} conflicts.`}</p><div className="ll1-grid">{rows.map(([cell, production]) => { const conflict = data.conflicts.some(item => item.cell === cell); return <div className={conflict ? 'll1-cell conflict' : 'll1-cell'} key={cell}><code>{conflict ? '▲ ' : ''}{cell}</code><span>{production}</span>{conflict && <small>Conflict</small>}</div> })}</div></div>
}
