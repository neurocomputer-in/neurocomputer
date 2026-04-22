'use client';

/**
 * NeuroEditor — view/edit/save any neuro + snapshots/rollback + create.
 *
 * Modes:
 *   mode="view"   → show src, Edit button unlocks textareas
 *   mode="edit"   → editable tabs, Save → POST /api/neuros/save
 *   mode="create" → blank templates, user types name, Save creates it
 *
 * A composite neuro (kind="skill.flow.*") just has a `children` list in
 * conf.json — editing the JSON IS editing the flow. A dedicated
 * children-picker below the Conf tab makes that one-click.
 */

import {
  Box, Flex, Heading, Text, Badge, Input, Button, Textarea,
  Tabs, TabList, Tab, TabPanels, TabPanel, Spinner, Code,
  Select, useToast, IconButton,
} from '@chakra-ui/react';
import { useEffect, useState, useMemo } from 'react';

export type NeuroEntry = {
  name: string;
  description: string;
  kind: string;
  kind_namespace: string;
  category?: string | null;
  color?: string | null;
  uses: string[];
  children: string[];
  inputs?: any[];
  outputs?: any[];
  summary_md?: string | null;
};

export type NeuroDetail = {
  describe: NeuroEntry;
  conf_src: string | null;
  code_src: string | null;
  prompt_src: string | null;
};

type Mode = 'view' | 'edit' | 'create';

type Props = {
  ideUrl: string;
  /** When null → create mode */
  loadedName: string | null;
  /** Already-fetched detail, if any. */
  detail: NeuroDetail | null;
  loading: boolean;
  allNeuros: NeuroEntry[];
  onSaved: (newName: string) => void;
  onDeleted: () => void;
  onNavigate: (name: string) => void;
};

const BLANK_CONF = (nm: string) => JSON.stringify({
  name: nm || 'new_neuro',
  description: 'one-line description of what this neuro does',
  kind: 'skill.leaf',
  category: 'custom',
}, null, 2);

const BLANK_CODE =
`"""<one-line module docstring>"""

async def run(state, **kw):
    # your logic here — return a dict, kwargs merge into state
    return {}
`;

export default function NeuroEditor({
  ideUrl, loadedName, detail, loading, allNeuros,
  onSaved, onDeleted, onNavigate,
}: Props) {
  const toast = useToast();
  const creating = loadedName === null;

  const [mode, setMode] = useState<Mode>(creating ? 'create' : 'view');
  const [createName, setCreateName] = useState('');
  const [draftConf, setDraftConf] = useState('');
  const [draftCode, setDraftCode] = useState('');
  const [draftPrompt, setDraftPrompt] = useState('');
  const [saveBusy, setSaveBusy] = useState(false);
  const [saveErr, setSaveErr] = useState<string[]>([]);
  const [snapshots, setSnapshots] = useState<string[]>([]);
  const [snapsBusy, setSnapsBusy] = useState(false);

  // Reset drafts when a new neuro is loaded
  useEffect(() => {
    if (creating) {
      setMode('create');
      setDraftConf(BLANK_CONF(createName));
      setDraftCode(BLANK_CODE);
      setDraftPrompt('');
      setSaveErr([]);
      return;
    }
    setMode('view');
    setDraftConf(detail?.conf_src || '');
    setDraftCode(detail?.code_src || '');
    setDraftPrompt(detail?.prompt_src || '');
    setSaveErr([]);
  }, [loadedName, detail?.conf_src, detail?.code_src, detail?.prompt_src]);

  // When user types a name in create mode, keep blank conf name in sync
  // (only if the user hasn't diverged the conf)
  useEffect(() => {
    if (creating) setDraftConf(BLANK_CONF(createName));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createName]);

  async function loadSnapshots() {
    if (!loadedName) return;
    setSnapsBusy(true);
    try {
      const r = await fetch(`${ideUrl}/api/snapshots/${encodeURIComponent(loadedName)}`);
      const data = await r.json();
      setSnapshots(data.snapshots || []);
    } finally {
      setSnapsBusy(false);
    }
  }

  async function save() {
    setSaveBusy(true);
    setSaveErr([]);

    // Parse conf JSON client-side so we fail fast w/ a clear message
    let confObj: any;
    try {
      confObj = JSON.parse(draftConf);
    } catch (e) {
      setSaveErr([`conf.json is not valid JSON: ${e}`]);
      setSaveBusy(false);
      return;
    }

    const targetName: string = mode === 'create'
      ? (createName.trim() || confObj.name)
      : loadedName!;
    if (!targetName) {
      setSaveErr(['neuro name is required']);
      setSaveBusy(false);
      return;
    }
    // keep conf.name in sync with target (dev_pipeline enforces it)
    if (confObj.name !== targetName) confObj.name = targetName;

    try {
      const r = await fetch(`${ideUrl}/api/neuros/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          neuro_name: targetName,
          conf:  confObj,
          code:  draftCode || null,
          prompt: draftPrompt || null,
          author: 'user',
        }),
      });
      const data = await r.json();
      if (!r.ok || data.ok === false) {
        setSaveErr(data.errors || [data.detail || `HTTP ${r.status}`]);
        setSaveBusy(false);
        return;
      }
      toast({
        status: 'success',
        title: mode === 'create' ? `Created "${targetName}"` : `Saved "${targetName}"`,
        description: data.snapshot ? `snapshot ${data.snapshot}` : undefined,
        duration: 3000,
      });
      setMode('view');
      onSaved(targetName);
    } catch (e) {
      setSaveErr([`network: ${e}`]);
    } finally {
      setSaveBusy(false);
    }
  }

  async function deleteNeuro() {
    if (!loadedName) return;
    if (!confirm(
      `Delete "${loadedName}"?\n\n` +
      `A snapshot will be taken first — you can recover via the ` +
      `history tab of a freshly created neuro with the same name, ` +
      `or by restoring from .neuros_history/${loadedName}/ on disk.`
    )) return;
    setSaveBusy(true);
    try {
      const r = await fetch(
        `${ideUrl}/api/neuros/${encodeURIComponent(loadedName)}`,
        { method: 'DELETE' },
      );
      const data = await r.json();
      if (!r.ok || data.ok === false) {
        toast({
          status: 'error',
          title: 'delete failed',
          description: (data.errors || [data.detail]).join(' · '),
        });
      } else {
        toast({
          status: 'success',
          title: `deleted "${loadedName}"`,
          description: data.snapshot ? `snapshot ${data.snapshot}` : undefined,
        });
        onDeleted();
      }
    } catch (e) {
      toast({ status: 'error', title: 'network', description: String(e) });
    } finally {
      setSaveBusy(false);
    }
  }

  async function rollback(ts: string) {
    if (!loadedName) return;
    if (!confirm(`Roll ${loadedName} back to ${ts}? Current version will be snapshotted first.`)) return;
    setSnapsBusy(true);
    try {
      const r = await fetch(
        `${ideUrl}/api/neuros/${encodeURIComponent(loadedName)}/rollback`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ snapshot_ts: ts }),
        },
      );
      const data = await r.json();
      if (!r.ok || data.ok === false) {
        toast({ status: 'error', title: 'rollback failed',
                description: (data.errors || [data.detail]).join(' · ') });
      } else {
        toast({ status: 'success', title: `rolled back to ${ts}` });
        onSaved(loadedName);
      }
    } finally {
      setSnapsBusy(false);
    }
  }

  // children picker: add/remove names from conf.json.children
  const confObj = useMemo(() => {
    try { return JSON.parse(draftConf); } catch { return null; }
  }, [draftConf]);
  const confChildren: string[] = confObj?.children || [];

  function updateChildren(next: string[]) {
    const obj = confObj ? { ...confObj } : {};
    if (next.length === 0) delete obj.children;
    else obj.children = next;
    setDraftConf(JSON.stringify(obj, null, 2));
  }

  if (loading) {
    return <Flex justify="center" p={8}><Spinner /></Flex>;
  }

  const dirty =
    mode !== 'view' && (
      draftConf !== (detail?.conf_src || (creating ? BLANK_CONF(createName) : '')) ||
      draftCode !== (detail?.code_src || (creating ? BLANK_CODE : '')) ||
      draftPrompt !== (detail?.prompt_src || '')
    );

  return (
    <Box>
      {/* Header row: name, kind, action buttons */}
      <Flex align="center" gap={3} mb={3} wrap="wrap">
        {creating ? (
          <Input
            placeholder="new_neuro_name"
            value={createName}
            onChange={(e) => setCreateName(e.target.value.replace(/[^a-zA-Z0-9_]/g, ''))}
            fontFamily="mono"
            size="sm"
            maxW="260px"
          />
        ) : (
          <Text fontFamily="mono" fontSize="lg">{loadedName}</Text>
        )}

        {detail?.describe && (
          <Badge colorScheme="purple">{detail.describe.kind}</Badge>
        )}
        {detail?.describe?.category && (
          <Text fontSize="xs" color="gray.500">{detail.describe.category}</Text>
        )}

        <Box flex="1" />

        {mode === 'view' && (
          <>
            <Button size="sm" colorScheme="purple" variant="outline"
                    onClick={() => setMode('edit')}>
              ✎ edit
            </Button>
            <Button size="sm" colorScheme="red" variant="ghost"
                    onClick={deleteNeuro} isLoading={saveBusy}>
              🗑 delete
            </Button>
          </>
        )}
        {mode !== 'view' && (
          <>
            <Button size="sm" variant="ghost"
                    onClick={() => {
                      setMode(creating ? 'create' : 'view');
                      // revert drafts
                      setDraftConf(detail?.conf_src || (creating ? BLANK_CONF(createName) : ''));
                      setDraftCode(detail?.code_src || (creating ? BLANK_CODE : ''));
                      setDraftPrompt(detail?.prompt_src || '');
                      setSaveErr([]);
                    }}>
              reset
            </Button>
            <Button
              size="sm"
              colorScheme="purple"
              onClick={save}
              isLoading={saveBusy}
              isDisabled={mode === 'create' && !createName.trim() && !confObj?.name}
            >
              {mode === 'create' ? '＋ create' : '💾 save'}
            </Button>
          </>
        )}
      </Flex>

      {detail?.describe?.description && mode === 'view' && (
        <Text fontSize="sm" color="gray.300" mb={3}>
          {detail.describe.description}
        </Text>
      )}

      {saveErr.length > 0 && (
        <Code display="block" p={3} mb={3} bg="red.900" color="red.100"
              whiteSpace="pre-wrap" fontSize="xs">
          {saveErr.join('\n')}
        </Code>
      )}

      <Tabs variant="enclosed" colorScheme="purple" size="sm">
        <TabList>
          <Tab>conf.json</Tab>
          <Tab>code.py</Tab>
          <Tab>prompt.txt</Tab>
          <Tab>flow · children</Tab>
          <Tab onClick={loadSnapshots}>history</Tab>
          {mode === 'view' && detail?.describe && <Tab>ports · uses</Tab>}
        </TabList>
        <TabPanels>
          {/* conf.json */}
          <TabPanel px={0}>
            <Textarea
              value={draftConf}
              onChange={(e) => setDraftConf(e.target.value)}
              isReadOnly={mode === 'view'}
              fontFamily="mono"
              fontSize="xs"
              minH="340px"
              bg="gray.900"
              border="1px solid"
              borderColor={mode === 'view' ? 'gray.800' : 'purple.700'}
            />
          </TabPanel>

          {/* code.py */}
          <TabPanel px={0}>
            <Textarea
              value={draftCode}
              onChange={(e) => setDraftCode(e.target.value)}
              isReadOnly={mode === 'view'}
              fontFamily="mono"
              fontSize="xs"
              minH="420px"
              bg="gray.900"
              border="1px solid"
              borderColor={mode === 'view' ? 'gray.800' : 'purple.700'}
            />
          </TabPanel>

          {/* prompt.txt */}
          <TabPanel px={0}>
            <Textarea
              value={draftPrompt}
              onChange={(e) => setDraftPrompt(e.target.value)}
              isReadOnly={mode === 'view'}
              fontFamily="mono"
              fontSize="xs"
              minH="340px"
              placeholder={mode === 'view' ? '(none)' : 'optional prompt.txt — jinja2 templating supported'}
              bg="gray.900"
              border="1px solid"
              borderColor={mode === 'view' ? 'gray.800' : 'purple.700'}
            />
          </TabPanel>

          {/* flow children */}
          <TabPanel px={0}>
            <Text fontSize="xs" color="gray.400" mb={2}>
              Flows/composites declare their sub-neuros in conf.children.
              Pick from library below to wire them.
            </Text>
            <Flex gap={2} mb={3} flexWrap="wrap">
              {confChildren.length === 0 && (
                <Text fontSize="sm" color="gray.500">(no children — leaf)</Text>
              )}
              {confChildren.map((c) => (
                <Badge
                  key={c}
                  colorScheme="cyan"
                  px={2} py={1}
                  cursor={mode === 'view' ? 'pointer' : 'default'}
                  onClick={() => mode === 'view' && onNavigate(c)}
                >
                  {c}
                  {mode !== 'view' && (
                    <IconButton
                      aria-label="remove"
                      size="xs"
                      variant="ghost"
                      ml={1}
                      icon={<>✕</>}
                      onClick={(e) => {
                        e.stopPropagation();
                        updateChildren(confChildren.filter((x) => x !== c));
                      }}
                    />
                  )}
                </Badge>
              ))}
            </Flex>
            {mode !== 'view' && (
              <Flex gap={2} align="center">
                <Select
                  size="sm"
                  placeholder="+ add child neuro"
                  bg="gray.800"
                  fontSize="xs"
                  onChange={(e) => {
                    const v = e.target.value;
                    if (!v || confChildren.includes(v)) return;
                    updateChildren([...confChildren, v]);
                    e.target.value = '';
                  }}
                >
                  {allNeuros
                    .filter((n) => !confChildren.includes(n.name))
                    .filter((n) => n.name !== loadedName)
                    .map((n) => (
                      <option key={n.name} value={n.name}>
                        {n.name}  ·  {n.kind}
                      </option>
                    ))}
                </Select>
              </Flex>
            )}
          </TabPanel>

          {/* history / snapshots */}
          <TabPanel px={0}>
            {creating ? (
              <Text fontSize="sm" color="gray.500">
                (history appears after first save)
              </Text>
            ) : snapsBusy ? (
              <Spinner />
            ) : snapshots.length === 0 ? (
              <Text fontSize="sm" color="gray.500">
                no snapshots yet — saves auto-snapshot up to 10 deep
              </Text>
            ) : (
              <Box>
                {snapshots.map((ts) => (
                  <Flex
                    key={ts}
                    align="center"
                    justify="space-between"
                    borderBottom="1px solid"
                    borderColor="gray.800"
                    py={2}
                  >
                    <Text fontFamily="mono" fontSize="xs">{ts}</Text>
                    <Button
                      size="xs"
                      variant="outline"
                      colorScheme="orange"
                      onClick={() => rollback(ts)}
                    >
                      ↶ rollback
                    </Button>
                  </Flex>
                ))}
              </Box>
            )}
          </TabPanel>

          {/* ports/uses — view-only summary */}
          {mode === 'view' && detail?.describe && (
            <TabPanel px={0}>
              <Heading size="xs" mb={2} color="gray.400">uses (deps)</Heading>
              <Flex flexWrap="wrap" gap={2} mb={4}>
                {(detail.describe.uses || []).length === 0
                  ? <Text fontSize="xs" color="gray.600">(none)</Text>
                  : detail.describe.uses.map((u) => (
                      <Badge key={u} colorScheme="purple" cursor="pointer"
                             onClick={() => onNavigate(u)}>↳ {u}</Badge>
                    ))}
              </Flex>
              <Heading size="xs" mb={2} color="gray.400">inputs</Heading>
              {(detail.describe.inputs || []).length === 0
                ? <Text fontSize="xs" color="gray.600">(none)</Text>
                : (detail.describe.inputs || []).map((p: any) => (
                    <Flex key={p.name} gap={3} align="baseline" mb={1}>
                      <Badge colorScheme="blue" fontSize="xs">{p.type}</Badge>
                      <Text fontFamily="mono" fontSize="sm">{p.name}</Text>
                      {p.description && (
                        <Text fontSize="xs" color="gray.500">— {p.description}</Text>
                      )}
                    </Flex>
                  ))}
              <Heading size="xs" mt={4} mb={2} color="gray.400">outputs</Heading>
              {(detail.describe.outputs || []).length === 0
                ? <Text fontSize="xs" color="gray.600">(none)</Text>
                : (detail.describe.outputs || []).map((p: any) => (
                    <Flex key={p.name} gap={3} align="baseline" mb={1}>
                      <Badge colorScheme="green" fontSize="xs">{p.type}</Badge>
                      <Text fontFamily="mono" fontSize="sm">{p.name}</Text>
                      {p.description && (
                        <Text fontSize="xs" color="gray.500">— {p.description}</Text>
                      )}
                    </Flex>
                  ))}
            </TabPanel>
          )}
        </TabPanels>
      </Tabs>
    </Box>
  );
}
