'use client';
import { useState } from 'react';
import { Project } from '@/types';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setSelectedProject } from '@/store/projectSlice';
import { fetchConversations, switchProjectTabs } from '@/store/conversationSlice';
import ProjectMenu from './ProjectMenu';

interface Props {
  projects: Project[];
}

export default function ProjectList({ projects }: Props) {
  const dispatch = useAppDispatch();
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const [menuProject, setMenuProject] = useState<Project | null>(null);
  const [menuPos, setMenuPos] = useState({ x: 0, y: 0 });

  const handleSelect = (id: string | null) => {
    if (id !== selectedProjectId) {
      dispatch(switchProjectTabs({
        fromProjectId: selectedProjectId, toProjectId: id,
        fromAgencyId: selectedWorkspaceId, toAgencyId: selectedWorkspaceId,
      }));
    }
    dispatch(setSelectedProject(id));
    dispatch(fetchConversations({ projectId: id, agencyId: selectedWorkspaceId }));
  };

  const handleContextMenu = (e: React.MouseEvent, p: Project) => {
    e.preventDefault();
    setMenuProject(p);
    setMenuPos({ x: e.clientX, y: e.clientY });
  };

  return (
    <>
      {projects.map((p, index) => {
        const isSelected = selectedProjectId === p.id;
        return (
          <div
            key={p.id ?? `noproj-${index}`}
            onClick={() => handleSelect(p.id)}
            onContextMenu={(e) => p.id ? handleContextMenu(e, p) : e.preventDefault()}
            style={{
              padding: '7px 10px',
              background: isSelected ? 'rgba(255,255,255,0.04)' : 'transparent',
              borderRadius: '6px',
              color: isSelected ? '#f7f8f8' : '#8a8f98',
              fontSize: '13px',
              marginBottom: '2px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              cursor: 'pointer',
              userSelect: 'none',
              fontWeight: isSelected ? 510 : 400,
            }}
            onMouseEnter={e => {
              if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.02)';
            }}
            onMouseLeave={e => {
              if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'transparent';
            }}
          >
            <div
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: p.color,
                flexShrink: 0,
              }}
            />
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {p.name}
            </span>
            {(p.conversationCount ?? 0) > 0 && (
              <span style={{ fontSize: '11px', color: '#62666d', fontWeight: 400 }}>
                {p.conversationCount}
              </span>
            )}
          </div>
        );
      })}
      {menuProject && (
        <ProjectMenu
          project={menuProject}
          position={menuPos}
          onClose={() => setMenuProject(null)}
        />
      )}
    </>
  );
}
