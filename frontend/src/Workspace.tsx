import { createContext, useContext } from 'react'
import type { DatasetKind, Health, Lottery, Scope } from './api'

export interface WorkspaceValue extends Scope {
  version: number
  health: Health | null
  refresh: () => void
  setLottery: (value: Lottery) => void
  setDatasetKind: (value: DatasetKind) => void
  openImport: () => void
  sync: () => void
  demo: () => void
}
export const Workspace = createContext<WorkspaceValue | null>(null)
export function useWorkspace() {
  const value = useContext(Workspace)
  if (!value) throw new Error('Missing workspace context')
  return value
}
