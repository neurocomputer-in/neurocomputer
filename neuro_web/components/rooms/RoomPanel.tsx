'use client';

import React, { useEffect, useRef, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7001';

interface Message {
  sender: string;
  text: string;
  ts: string;
}

interface Room {
  id: string;
  name: string;
  agents: string[];
  transcript: Message[];
  status: string;
  turn_policy: string;
  max_turns: number;
}

export function RoomPanel() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [selected, setSelected] = useState<Room | null>(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [newName, setNewName] = useState('');
  const [newAgents, setNewAgents] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  const fetchRooms = async () => {
    const res = await fetch(`${API}/api/rooms`);
    const data = await res.json();
    setRooms(data.rooms || []);
  };

  const fetchRoom = async (id: string) => {
    const res = await fetch(`${API}/api/rooms/${id}`);
    const data = await res.json();
    setSelected(data);
  };

  useEffect(() => { fetchRooms(); }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [selected?.transcript]);

  const createRoom = async () => {
    if (!newName || !newAgents) return;
    const agents = newAgents.split(',').map(s => s.trim()).filter(Boolean);
    await fetch(`${API}/api/rooms`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName, agents }),
    });
    setNewName(''); setNewAgents('');
    await fetchRooms();
  };

  const sendMessage = async () => {
    if (!selected || !input.trim()) return;
    setLoading(true);
    const res = await fetch(`${API}/api/rooms/${selected.id}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: input }),
    });
    setInput('');
    const data = await res.json();
    setSelected(data);
    setLoading(false);
  };

  const closeRoom = async (id: string) => {
    await fetch(`${API}/api/rooms/${id}`, { method: 'DELETE' });
    if (selected?.id === id) setSelected(null);
    await fetchRooms();
  };

  return (
    <div style={{ display: 'flex', height: '100%', fontFamily: 'monospace', fontSize: 13 }}>
      {/* Sidebar */}
      <div style={{ width: 200, borderRight: '1px solid #333', padding: 8, overflowY: 'auto' }}>
        <div style={{ color: '#a78bfa', fontWeight: 700, marginBottom: 8 }}>Rooms</div>
        {rooms.map(r => (
          <div key={r.id}
            onClick={() => fetchRoom(r.id)}
            style={{ padding: '4px 6px', cursor: 'pointer', borderRadius: 4,
              background: selected?.id === r.id ? '#1e1b4b' : 'transparent',
              color: r.status === 'closed' ? '#666' : '#eee', marginBottom: 2 }}>
            {r.name}
            <span style={{ color: '#666', fontSize: 10, marginLeft: 4 }}>
              [{r.agents.length}]
            </span>
          </div>
        ))}
        <div style={{ marginTop: 12, color: '#888', fontSize: 11 }}>New room</div>
        <input value={newName} onChange={e => setNewName(e.target.value)}
          placeholder="name" style={inputStyle} />
        <input value={newAgents} onChange={e => setNewAgents(e.target.value)}
          placeholder="agents (comma-sep)" style={inputStyle} />
        <button onClick={createRoom} style={btnStyle}>Create</button>
      </div>

      {/* Transcript */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {selected ? (
          <>
            <div style={{ padding: '6px 12px', borderBottom: '1px solid #333', display: 'flex',
              alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ color: '#a78bfa', fontWeight: 700 }}>{selected.name}</span>
              <span style={{ color: '#666', fontSize: 11 }}>
                {selected.agents.join(', ')} · {selected.turn_policy} · {selected.status}
              </span>
              {selected.status !== 'closed' && (
                <button onClick={() => closeRoom(selected.id)} style={{ ...btnStyle, color: '#f87171' }}>
                  Close
                </button>
              )}
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
              {selected.transcript.map((msg, i) => (
                <div key={i} style={{ marginBottom: 8 }}>
                  <span style={{ color: msg.sender === 'user' ? '#67e8f9' : '#a78bfa', fontWeight: 600 }}>
                    {msg.sender}:
                  </span>{' '}
                  <span style={{ color: '#eee' }}>{msg.text}</span>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
            {selected.status !== 'closed' && (
              <div style={{ padding: 8, borderTop: '1px solid #333', display: 'flex', gap: 6 }}>
                <input value={input} onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && sendMessage()}
                  placeholder="Message…" style={{ ...inputStyle, flex: 1 }} />
                <button onClick={sendMessage} disabled={loading} style={btnStyle}>
                  {loading ? '…' : 'Send'}
                </button>
              </div>
            )}
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#555' }}>Select a room or create one</div>
        )}
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  background: '#111', border: '1px solid #333', borderRadius: 4,
  color: '#eee', padding: '4px 6px', width: '100%', marginBottom: 4, fontSize: 12,
};

const btnStyle: React.CSSProperties = {
  background: '#1e1b4b', border: '1px solid #4c1d95', borderRadius: 4,
  color: '#a78bfa', padding: '4px 8px', cursor: 'pointer', fontSize: 12,
};
