import React from 'react'

export function tokenizeInput(value, terminals = []) {
  if (value.trim() === '' || value.trim() === 'ε' || value.trim().toLowerCase() === 'epsilon') return []
  const ordered = [...terminals].sort((left, right) => right.length - left.length || left.localeCompare(right))
  const tokens = []
  for (const piece of value.trim().split(/\s+/)) {
    let index = 0
    while (index < piece.length) {
      const token = ordered.find(candidate => piece.startsWith(candidate, index))
      if (!token) return { error: `Unknown symbol '${piece[index]}'.` }
      tokens.push(token)
      index += token.length
    }
  }
  return tokens
}

export function simulateAutomaton(automaton, tokens) {
  const start = automaton?.start || automaton?.start_state
  let active = new Set(start ? [start] : [])
  const states = [Array.from(active)]
  for (const token of tokens) {
    active = new Set((automaton?.transitions || [])
      .filter(transition => active.has(transition.from) && transition.symbol === token)
      .map(transition => transition.to))
    states.push(Array.from(active))
  }
  return { accepted: Array.from(active).some(state => automaton?.final_states?.includes(state)), states, activeStates: Array.from(active) }
}

export default function AutomatonDiagram({ automaton, active = [] }) {
  const states = automaton?.states || []
  const transitions = automaton?.transitions || []
  const activeSet = new Set(active)
  const width = Math.max(520, states.length * 150 + 80)
  const height = 220
  const positions = Object.fromEntries(states.map((state, index) => [state, { x: 40 + index * 150, y: 110 }]))
  const grouped = transitions.reduce((groups, transition) => {
    const key = `${transition.from}->${transition.to}`
    groups[key] ||= []
    groups[key].push(transition.symbol)
    return groups
  }, {})
  return <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Finite automaton state diagram">
    <defs><marker id="automaton-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="currentColor" /></marker></defs>
    {Object.entries(grouped).map(([key, symbols]) => {
      const [from, to] = key.split('->')
      const source = positions[from]
      const target = positions[to]
      if (!source || !target) return null
      const same = from === to
      const mid = (source.x + target.x) / 2
      const curve = same ? `M ${source.x} 82 C ${source.x - 48} 10 ${source.x + 48} 10 ${source.x} 82` : `M ${source.x} 110 Q ${mid} ${source.y - 70} ${target.x} 110`
      return <g key={key}><path d={curve} className="edge" markerEnd="url(#automaton-arrow)" /><text x={same ? source.x : mid} y={same ? 28 : 58} textAnchor="middle" className="edge-label">{symbols.join(', ')}</text></g>
    })}
    {states.map(state => {
      const position = positions[state]
      const final = automaton.final_states?.includes(state)
      const isStart = (automaton.start || automaton.start_state) === state
      const labelClass = state.length > 3 ? 'state-label compact' : 'state-label'
      return <g key={state} className={activeSet.has(state) ? 'active-state' : ''}>
        {isStart && <line x1={position.x - 42} y1={110} x2={position.x - 28} y2={110} className="edge" markerEnd="url(#automaton-arrow)" />}
        <circle cx={position.x} cy={position.y} r="30" className="state-node" />
        {final && <circle cx={position.x} cy={position.y} r="24" className="final-node" />}
        <text x={position.x} y={position.y + 5} textAnchor="middle" className={labelClass}>{state}</text>
      </g>
    })}
  </svg>
}
