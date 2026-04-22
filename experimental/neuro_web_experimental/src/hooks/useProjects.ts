'use client';
import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  fetchProjects, createProject, deleteProject, setSelectedProject,
} from '@/store/projectSlice';

export function useProjects() {
  const dispatch = useAppDispatch();
  const projects = useAppSelector(s => s.projects.projects);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const loading = useAppSelector(s => s.projects.loading);

  const refresh = useCallback(() => dispatch(fetchProjects(selectedWorkspaceId)), [dispatch, selectedWorkspaceId]);

  const create = useCallback(
    (name: string, color: string, description?: string) =>
      dispatch(createProject({ name, color, description, workspaceId: selectedWorkspaceId })),
    [dispatch, selectedWorkspaceId]
  );

  const remove = useCallback(
    (id: string) => dispatch(deleteProject(id)),
    [dispatch]
  );

  const select = useCallback(
    (id: string | null) => dispatch(setSelectedProject(id)),
    [dispatch]
  );

  return { projects, selectedProjectId, loading, refresh, create, remove, select };
}
