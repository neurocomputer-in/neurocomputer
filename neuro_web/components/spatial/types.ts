export type NodeKind = 'chat' | 'terminal' | 'dashboard';

export interface NodeModel {
  cid: string;
  title: string;
  kind: NodeKind;
  projectId: string | null;
  position: [number, number, number];
  active: boolean;
  running?: boolean;
}
