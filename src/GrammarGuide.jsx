import React, { useState } from 'react'
import { ArrowDown, ArrowLeft, BookOpen, Check, ChevronRight, GitBranch, Play, X } from 'lucide-react'

const grammarTypes = [
  {
    id: 'type0',
    type: 'TYPE 0',
    name: 'Unrestricted Grammar',
    model: 'Turing Machine',
    definition: 'An unrestricted grammar has very few restrictions on its productions. The left-hand side must contain at least one non-terminal.',
    production: 'α → β, where α contains at least one non-terminal.',
    example: ['S -> AB', 'AB -> BA'],
    language: 'Recursively enumerable languages',
    relevance: 'The most general class in the hierarchy, useful for understanding the full expressive power of formal grammars.',
    characteristics: ['Most general grammar class.', 'Production rules have minimal restrictions.', 'More powerful than Type 1, Type 2, and Type 3 grammars.'],
    where: 'Type 0 is the most general class in the Chomsky hierarchy.',
    start: 'S'
  },
  {
    id: 'type1',
    type: 'TYPE 1',
    name: 'Context-Sensitive Grammar',
    model: 'Linear Bounded Automaton (LBA)',
    definition: 'A context-sensitive grammar generally uses non-contracting productions. The standard formal definition also has special handling for a start-symbol epsilon production.',
    production: 'αAβ → αγβ, or |LHS| ≤ |RHS| for non-contracting rules.',
    example: ['S -> aSBC | abc', 'CB -> BC', 'aB -> ab', 'bB -> bb', 'bC -> bc', 'cC -> cc'],
    language: 'Context-sensitive languages',
    relevance: 'The surrounding context can affect how a non-terminal is replaced, making this class more expressive than context-free grammars.',
    characteristics: ['More restrictive than Type 0.', 'Productions generally do not decrease string length.', 'Replacement can depend on surrounding context.'],
    analysis: ['CB → BC', 'LHS length = 2', 'RHS length = 2', 'Therefore the production is non-contracting.'],
    where: 'Type 1 sits between unrestricted and context-free grammars.',
    start: 'S'
  },
  {
    id: 'type2',
    type: 'TYPE 2',
    name: 'Context-Free Grammar',
    model: 'Pushdown Automaton (PDA)',
    definition: 'A context-free grammar has exactly one non-terminal on the left-hand side of every production.',
    production: 'A → α, where A is a single non-terminal.',
    example: ['S -> aSb | ε'],
    language: 'L = { aⁿbⁿ | n ≥ 0 }',
    relevance: 'Context-free grammars are central to programming-language syntax and compiler parsing.',
    characteristics: ['Exactly one non-terminal on the left-hand side.', 'Supports recursive structures.', 'Used in syntax analysis and parsing.'],
    derivation: ['ε', 'ab', 'aabb', 'aaabbb', '...'],
    operations: ['FIRST', 'FOLLOW', 'LL(1) analysis', 'Parse tree', 'Remove epsilon-productions', 'Remove unit productions', 'Remove useless symbols', 'Remove left recursion', 'Left factoring', 'CNF conversion'],
    where: 'Type 2 is the main grammar class used for compiler syntax.',
    start: 'S'
  },
  {
    id: 'type3',
    type: 'TYPE 3',
    name: 'Regular Grammar',
    model: 'Finite Automaton',
    definition: 'A regular grammar has productions in a regular right-linear or left-linear form.',
    production: 'Right-linear: A → aB, A → a, A → ε. Left-linear: A → Ba, A → a, A → ε.',
    example: ['S -> aA | b', 'A -> aS | a'],
    language: 'Regular languages',
    relevance: 'Regular grammars are closely related to lexical analysis, pattern matching, and finite automata.',
    characteristics: ['Most restricted grammar class.', 'Can be represented using finite automata.', 'Closely related to DFA and NFA.'],
    automata: ['Regular Grammar', 'NFA', 'DFA'],
    where: 'Type 3 is the most restricted class in the Chomsky hierarchy.',
    start: 'S'
  }
]

const comparisonRows = grammarTypes.map(item => ({ type: item.type.replace('TYPE ', 'Type '), grammar: item.name, restriction: item.production, model: item.model }))

export default function GrammarGuide({ onBack, onTryGrammar, currentGrammar }) {
  const [selectedType, setSelectedType] = useState(null)
  const [pendingExample, setPendingExample] = useState(null)
  const selected = grammarTypes.find(item => item.id === selectedType)

  function tryGrammar(item) {
    if (currentGrammar.trim()) {
      setPendingExample(item)
      return
    }
    onTryGrammar(item.example.join('\n'), item.start)
  }

  function confirmExample() {
    if (!pendingExample) return
    onTryGrammar(pendingExample.example.join('\n'), pendingExample.start)
    setPendingExample(null)
  }

  return <main className="guide-view">
    <div className="guide-topline"><button className="guide-back" onClick={onBack}><ArrowLeft size={16} /> Back to Grammar Assistant</button><span className="eyebrow">REFERENCE / GRAMMAR THEORY</span></div>
    <div className="guide-heading"><div><p className="eyebrow">GRAMMAR GUIDE</p><h2>Grammar Guide</h2><p>Understand formal grammars, the Chomsky hierarchy, and the role of each grammar type in Automata Theory and Compiler Design.</p></div><BookOpen size={28} /></div>

    <section className="guide-hierarchy" aria-labelledby="hierarchy-title">
      <div className="guide-section-heading"><div><p className="eyebrow">THE BIG PICTURE</p><h3 id="hierarchy-title">Chomsky Hierarchy</h3></div><span>Increasing restriction → increasing specialization</span></div>
      <div className="hierarchy-flow">{grammarTypes.map((item, index) => <React.Fragment key={item.id}><button className={selectedType === item.id ? 'hierarchy-node selected' : 'hierarchy-node'} onClick={() => setSelectedType(item.id)}><strong>{item.type}</strong><span>{item.name}</span><small>{item.model}</small></button>{index < grammarTypes.length - 1 && <ArrowDown className="hierarchy-arrow" size={18} />}</React.Fragment>)}</div>
      <p className="guide-instruction">Select a grammar type to explore its definition, production rules, computational model, examples, and applications.</p>
    </section>

    <section className="guide-type-grid" aria-label="Grammar types">{grammarTypes.map(item => <button className={selectedType === item.id ? 'guide-type-card selected' : 'guide-type-card'} key={item.id} onClick={() => setSelectedType(item.id)}><span>{item.type}</span><strong>{item.name}</strong><small>{item.model}</small><ChevronRight size={16} /></button>)}</section>

    {selected && <GuideDetail item={selected} onTry={() => tryGrammar(selected)} />}

    <section className="guide-comparison" aria-labelledby="comparison-title"><div className="guide-section-heading"><div><p className="eyebrow">REFERENCE TABLE</p><h3 id="comparison-title">Chomsky Hierarchy at a Glance</h3></div></div><div className="guide-table-wrap"><table><thead><tr><th>Type</th><th>Grammar</th><th>Production restriction</th><th>Machine</th></tr></thead><tbody>{comparisonRows.map(row => <tr key={row.type}><td>{row.type}</td><td>{row.grammar}</td><td>{row.restriction}</td><td>{row.model}</td></tr>)}</tbody></table></div><p className="hierarchy-inclusion">Type 3 ⊂ Type 2 ⊂ Type 1 ⊂ Type 0</p></section>

    {pendingExample && <div className="guide-confirm-backdrop" role="presentation"><div className="guide-confirm" role="dialog" aria-modal="true" aria-labelledby="guide-confirm-title"><button className="guide-confirm-close" onClick={() => setPendingExample(null)} aria-label="Cancel loading example"><X size={16} /></button><p className="eyebrow">LOAD EXAMPLE</p><h3 id="guide-confirm-title">Load example grammar?</h3><p>Your current grammar will be replaced by the {pendingExample.name} example.</p><div className="guide-confirm-actions"><button className="ghost-button" onClick={() => setPendingExample(null)}>Cancel</button><button className="secondary-button" onClick={confirmExample}><Play size={15} /> Load Example</button></div></div></div>}
  </main>
}

function GuideDetail({ item, onTry }) {
  return <article className="guide-detail"><div className="guide-detail-header"><div><p className="eyebrow">{item.type}</p><h3>{item.name}</h3></div><div className="model-badge">{item.model}</div></div><div className="guide-detail-grid"><GuideBlock title="Definition"><p>{item.definition}</p></GuideBlock><GuideBlock title="Production Form"><code>{item.production}</code></GuideBlock><GuideBlock title="Example"><pre>{item.example.join('\n')}</pre></GuideBlock><GuideBlock title="Computational Model"><p>{item.model}</p></GuideBlock><GuideBlock title="Key Characteristics"><ul>{item.characteristics.map(value => <li key={value}>{value}</li>)}</ul></GuideBlock><GuideBlock title="Example Language"><p>{item.language}</p></GuideBlock><GuideBlock title="Compiler / Automata Relevance"><p>{item.relevance}</p></GuideBlock>{item.analysis && <GuideBlock title="Production Analysis"><pre>{item.analysis.join('\n')}</pre></GuideBlock>}{item.derivation && <GuideBlock title="Derivation"><pre>{item.derivation.join('\n')}</pre></GuideBlock>}{item.operations && <GuideBlock title="Common Compiler / Grammar Operations"><ul className="operation-list">{item.operations.map(value => <li key={value}><Check size={14} /> {value}</li>)}</ul></GuideBlock>}{item.automata && <GuideBlock title="Automata Connection"><div className="automata-flow">{item.automata.map((value, index) => <React.Fragment key={value}><span>{value}</span>{index < item.automata.length - 1 && <ArrowDown size={15} />}</React.Fragment>)}</div></GuideBlock>}</div><div className="guide-where"><strong>Where it fits</strong><span>{item.where}</span></div><button className="primary-button guide-try" onClick={onTry}><Play size={15} /> Try This Grammar</button></article>
}

function GuideBlock({ title, children }) {
  return <div className="guide-block"><h4>{title}</h4>{children}</div>
}
