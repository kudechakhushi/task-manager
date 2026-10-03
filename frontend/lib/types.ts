export interface User { id: string; name: string | null; email: string; picture?: string }

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: "pending" | "completed";
  priority: "low" | "medium" | "high";
  due_date: string | null;
  created_by: string;
  assigned_to: string | null;
  creator?: { name: string | null; email: string };
  assignee?: { name: string | null; email: string } | null;
}