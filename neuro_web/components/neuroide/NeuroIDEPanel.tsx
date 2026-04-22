'use client';

/**
 * NeuroIDE — 3D neuro library + editor, as a pane-mountable component.
 *
 * Same capability set as the old /graph page, but fills its container
 * rather than the viewport so it can live inside a PaneFrame alongside
 * chat and terminal panes. The standalone /graph page is a thin wrapper
 * around this component (kept for deep-linking).
 */

import { useEffect, useState, useMemo } from 'react';
import {
  Box,
  Flex,
  Heading,
  Text,
  Badge,
  Input,
  Textarea,
  Button,
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  Code,
  Spinner,
  useDisclosure,
} from '@chakra-ui/react';
import Graph3D from './Graph3D';
import NeuroEditor from './NeuroEditor';
import SpatialErrorBoundary from '@/components/spatial/SpatialErrorBoundary';
import { isWebGLAvailable } from '@/components/three/webglSupport';

const IDE_URL =
  process.env.NEXT_PUBLIC_IDE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://localhost:7001';

type NeuroEntry = {
  name: string;
  description: string;
  kind: string;
  kind_namespace: string;
  category?: string | null;
  icon?: string | null;
  color?: string | null;
  summary_md?: string | null;
  scope?: string | null;
  uses: string[];
  children: string[];
  inputs: { name: string; type: string; description?: string; optional?: boolean }[];
  outputs: { name: string; type: string; description?: string; optional?: boolean }[];
};

type NeuroDetail = {
  describe: NeuroEntry;
  conf_src: string | null;
  code_src: string | null;
  prompt_src: string | null;
  layout: any;
};

const NS_COLORS: Record<string, string> = {
  skill:      'gray',
  prompt:     'purple',
  context:    'cyan',
  memory:     'teal',
  model:      'orange',
  instruction:'yellow',
  code:       'green',
  agent:      'pink',
  library:    'blackAlpha',
};

export default function NeuroIDEPanel() {
  const [neuros, setNeuros] = useState<NeuroEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<NeuroDetail | null>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const { isOpen, onOpen, onClose } = useDisclosure();

  const [chatOpen, setChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [chatTarget, setChatTarget] = useState<string>('');
  const [chatLog, setChatLog] = useState<
    { role: 'user' | 'system'; text: string; meta?: any }[]
  >([]);
  const [chatBusy, setChatBusy] = useState(false);

  async function refreshNeuros() {
    try {
      const r = await fetch(`${IDE_URL}/api/neuros`);
      const data = await r.json();
      setNeuros(data.neuros || []);
    } catch (e) { /* silent */ }
  }

  async function sendModify() {
    const text = chatInput.trim();
    if (!text || chatBusy) return;
    setChatBusy(true);
    setChatLog((log) => [...log, { role: 'user', text }]);
    setChatInput('');
    try {
      const r = await fetch(`${IDE_URL}/api/modify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_request: text,
          target_neuro: chatTarget || undefined,
          max_retries: 2,
        }),
      });
      const data = await r.json();
      const summary =
        (data.reply || '').trim() ||
        (data.errors || []).join(' · ') ||
        JSON.stringify(data);
      setChatLog((log) => [...log, { role: 'system', text: summary, meta: data }]);
      if (data.ok) refreshNeuros();
    } catch (e) {
      setChatLog((log) => [...log, { role: 'system', text: `fetch failed: ${e}` }]);
    } finally {
      setChatBusy(false);
    }
  }

  useEffect(() => {
    fetch(`${IDE_URL}/api/neuros`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((data) => setNeuros(data.neuros || []))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return neuros;
    return neuros.filter(
      (n) =>
        n.name.toLowerCase().includes(q) ||
        (n.description || '').toLowerCase().includes(q) ||
        (n.category || '').toLowerCase().includes(q) ||
        n.kind.toLowerCase().includes(q),
    );
  }, [neuros, query]);

  const nsCounts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const n of filtered) {
      const ns = n.kind_namespace || 'misc';
      c[ns] = (c[ns] || 0) + 1;
    }
    return c;
  }, [filtered]);

  async function openDetail(name: string) {
    setCreating(false);
    setSelectedName(name);
    setDetailLoading(true);
    onOpen();
    try {
      const r = await fetch(`${IDE_URL}/api/neuros/${encodeURIComponent(name)}`);
      setSelected(await r.json());
    } catch {
      setSelected(null);
    } finally {
      setDetailLoading(false);
    }
  }

  function openCreate() {
    setCreating(true);
    setSelected(null);
    setSelectedName(null);
    onOpen();
  }

  async function handleSaved(newName: string) {
    await refreshNeuros();
    setCreating(false);
    setSelectedName(newName);
    setDetailLoading(true);
    try {
      const r = await fetch(`${IDE_URL}/api/neuros/${encodeURIComponent(newName)}`);
      setSelected(await r.json());
    } finally {
      setDetailLoading(false);
    }
  }

  if (loading) {
    return (
      <Flex align="center" justify="center" h="100%">
        <Spinner size="xl" />
      </Flex>
    );
  }

  if (error) {
    return (
      <Box p={8}>
        <Heading size="md" mb={4}>Can't reach IDE backend</Heading>
        <Text>Expected at <Code>{IDE_URL}</Code>. Start the dev backend:</Text>
        <Code display="block" p={4} mt={4} whiteSpace="pre">
          python3 server.py   # listens on :7001
        </Code>
        <Text mt={4} color="red.400">Fetch error: {error}</Text>
      </Box>
    );
  }

  const nsOrder = [
    'agent', 'skill', 'prompt', 'context', 'memory',
    'model', 'instruction', 'code', 'dev', 'ide',
    'system', 'media', 'util', 'upwork', 'library',
  ];
  const sortedNs = Object.keys(nsCounts).sort((a, b) => {
    const ia = nsOrder.indexOf(a);
    const ib = nsOrder.indexOf(b);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });

  return (
    <Box h="100%" w="100%" overflow="hidden" bg="black" color="white" position="relative">
      <Box position="absolute" inset={0}>
        <Graph3DMount neuros={filtered} onSelect={openDetail} />
      </Box>

      {/* top-left HUD */}
      <Box
        position="absolute" top={3} left={3}
        bg="rgba(10,10,20,0.6)" backdropFilter="blur(8px)"
        border="1px solid" borderColor="whiteAlpha.200"
        borderRadius="md" p={3} maxW="290px"
      >
        <Heading size="sm" mb={2}>
          🧠 neuroIDE <Text as="span" fontSize="xs" color="gray.400">
            ({neuros.length} total · {filtered.length} shown)
          </Text>
        </Heading>
        <Text fontSize="xs" color="gray.400" mb={2}>
          drag to rotate · scroll to zoom · click node to inspect · composite → expand
        </Text>
        <Flex gap={1} flexWrap="wrap">
          {sortedNs.map(ns => (
            <Badge key={ns} colorScheme={NS_COLORS[ns] || 'gray'} fontSize="xs" variant="subtle">
              {ns} · {nsCounts[ns]}
            </Badge>
          ))}
        </Flex>
      </Box>

      {/* top-right HUD */}
      <Flex position="absolute" top={3} right={3} gap={2} align="center">
        <Input
          placeholder="filter…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          bg="rgba(10,10,20,0.7)" backdropFilter="blur(8px)"
          border="1px solid" borderColor="whiteAlpha.200"
          color="white" fontSize="sm" w="240px" size="sm"
        />
        <Button size="sm" colorScheme="purple" onClick={openCreate} boxShadow="lg">
          ＋ new
        </Button>
      </Flex>

      <Drawer isOpen={isOpen} onClose={onClose} size="xl" placement="right">
        <DrawerOverlay />
        <DrawerContent bg="gray.950" color="white">
          <DrawerCloseButton />
          <DrawerHeader borderBottom="1px solid" borderColor="gray.800">
            <Text fontSize="sm" color="gray.400">
              {creating ? '＋ create new neuro' : 'neuro editor'}
            </Text>
          </DrawerHeader>
          <DrawerBody>
            <NeuroEditor
              ideUrl={IDE_URL}
              loadedName={selectedName}
              detail={selected}
              loading={detailLoading}
              allNeuros={neuros}
              onSaved={handleSaved}
              onDeleted={() => { refreshNeuros(); onClose(); }}
              onNavigate={openDetail}
            />
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      {/* AI-modify floating panel — pane-scoped */}
      {!chatOpen ? (
        <Button
          position="absolute" bottom="16px" right="16px"
          size="md" colorScheme="purple" borderRadius="full" boxShadow="lg"
          onClick={() => setChatOpen(true)}
        >
          ✨ AI modify
        </Button>
      ) : (
        <Box
          position="absolute" bottom="16px" right="16px"
          w="380px" maxW="calc(100% - 32px)" h="480px" maxH="calc(100% - 32px)"
          bg="gray.900" border="1px solid" borderColor="purple.700"
          borderRadius="lg" boxShadow="xl"
          display="flex" flexDirection="column" overflow="hidden"
        >
          <Flex p={3} bg="gray.800" borderBottom="1px solid" borderColor="gray.700"
                justify="space-between" align="center">
            <Text fontWeight="bold" fontSize="sm">🧠 AI modify</Text>
            <Button size="xs" variant="ghost" onClick={() => setChatOpen(false)}>✕</Button>
          </Flex>
          <Box p={2} borderBottom="1px solid" borderColor="gray.800">
            <Input
              size="sm" placeholder="target neuro (optional)"
              value={chatTarget} onChange={(e) => setChatTarget(e.target.value)}
              bg="gray.950" border="1px solid" borderColor="gray.700"
              fontFamily="mono" fontSize="xs"
            />
          </Box>
          <Box flex={1} overflowY="auto" p={3} fontSize="sm">
            {chatLog.length === 0 ? (
              <Text color="gray.500" fontSize="xs">
                examples: "make advisor's tone terse", "add a neuro that reverses a string"
              </Text>
            ) : chatLog.map((m, i) => (
              <Box key={i} mb={3} p={2} borderRadius="md"
                   bg={m.role === 'user' ? 'purple.900' : 'gray.800'}>
                <Text fontSize="xs" color="gray.400" mb={1}>
                  {m.role}
                  {m.meta?.action && ` · ${m.meta.action}`}
                  {m.meta?.neuro_name && ` · ${m.meta.neuro_name}`}
                  {m.meta?.attempts && ` · ${m.meta.attempts} attempt(s)`}
                </Text>
                <Text fontSize="sm" whiteSpace="pre-wrap">{m.text}</Text>
                {m.meta?.errors && m.meta.errors.length > 0 && (
                  <Code display="block" mt={2} p={2} fontSize="xs"
                        bg="red.900" color="red.100">
                    {m.meta.errors.join('\n')}
                  </Code>
                )}
              </Box>
            ))}
          </Box>
          <Flex p={2} gap={2} borderTop="1px solid" borderColor="gray.800">
            <Textarea
              size="sm" value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendModify();
                }
              }}
              placeholder="describe the change u want..."
              rows={2} bg="gray.950"
              border="1px solid" borderColor="gray.700" resize="none"
            />
            <Button size="sm" colorScheme="purple" onClick={sendModify}
                    isLoading={chatBusy} isDisabled={!chatInput.trim()}>
              send
            </Button>
          </Flex>
        </Box>
      )}
    </Box>
  );
}

function WebGLFallback({ msg }: { msg: string }) {
  return (
    <Flex h="100%" w="100%" align="center" justify="center" bg="black" color="gray.300" p={6} textAlign="center">
      <Box maxW="480px">
        <Heading size="sm" mb={2}>3D view unavailable</Heading>
        <Text fontSize="xs" color="gray.400">{msg}</Text>
        <Text fontSize="xs" color="gray.500" mt={3}>
          Check chrome://gpu (WebGL row), enable hardware acceleration in browser settings, or close other tabs using WebGL and reload.
        </Text>
      </Box>
    </Flex>
  );
}

function Graph3DMount(props: { neuros: any[]; onSelect: (name: string) => void }) {
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => { setOk(isWebGLAvailable()); }, []);
  if (ok === null) return null;
  if (!ok) return <WebGLFallback msg="Your browser cannot create a WebGL context. This can happen when too many 3D views are open, or when hardware acceleration is disabled." />;
  return (
    <SpatialErrorBoundary fallback={<WebGLFallback msg="The 3D graph crashed while initializing. Reload the page to retry." />}>
      <Graph3D neuros={props.neuros} onSelect={props.onSelect} />
    </SpatialErrorBoundary>
  );
}
