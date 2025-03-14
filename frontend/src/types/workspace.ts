// 工作组相关类型
export interface WorkgroupBase {
  name: string;
  description?: string | null;
}

export interface WorkgroupCreate extends WorkgroupBase {}

export interface Workgroup extends WorkgroupBase {
  id: number;
  created_at: string | null;
}

// 工作空间相关类型
export interface WorkspaceBase {
  name: string;
  description?: string | null;
  group_id: number;
}

export interface WorkspaceCreate extends WorkspaceBase {}

export interface Workspace extends WorkspaceBase {
  id: number;
  created_at: string | null;
  updated_at: string | null;
  document_count: number;
}

// 添加这行使其成为模块
export {}; 