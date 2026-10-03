"use client";
import { useCallback, useEffect, useMemo, useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Task, User } from "@/lib/types";

type View = "assigned" | "created";
type StatusFilter = "all" | "pending" | "completed";
type FormErrors = { title?: string; description?: string; dueDate?: string };

const PRIORITY_STYLES: Record<string, string> = {
  high: "bg-red-50 text-red-700 ring-red-200",
  medium: "bg-amber-50 text-amber-700 ring-amber-200",
  low: "bg-emerald-50 text-emerald-700 ring-emerald-200",
};

const PRIORITY_BORDER: Record<string, string> = {
  high: "border-l-red-500",
  medium: "border-l-amber-400",
  low: "border-l-emerald-500",
};

function initials(name?: string | null) {
  if (!name) return "?";
  return name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

// Today as YYYY-MM-DD in local time, so it compares with date strings from the form and the API
function todayString() {
  return new Date().toLocaleDateString("en-CA");
}

export default function Dashboard() {
  const router = useRouter();
  const [me, setMe] = useState<User | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [view, setView] = useState<View>("assigned");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Create-task form fields
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [assignedTo, setAssignedTo] = useState("");
  const [priority, setPriority] = useState("medium");
  const [dueDate, setDueDate] = useState("");
  const [formErrors, setFormErrors] = useState<FormErrors>({});

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      setTasks(await apiFetch<Task[]>(`/api/tasks?view=${view}`));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [view]);

  useEffect(() => {
    if (!localStorage.getItem("token")) {
      router.replace("/login");
      return;
    }
    apiFetch<User>("/api/me").then(setMe).catch((e) => setError(e.message));
    apiFetch<User[]>("/api/users").then(setUsers).catch((e) => setError(e.message));
  }, [router]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const isOverdue = (t: Task) =>
    t.status === "pending" && !!t.due_date && t.due_date < todayString();

  const stats = useMemo(
    () => ({
      total: tasks.length,
      pending: tasks.filter((t) => t.status === "pending").length,
      completed: tasks.filter((t) => t.status === "completed").length,
      overdue: tasks.filter(isOverdue).length,
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [tasks]
  );

  const visibleTasks = useMemo(() => {
    const q = search.trim().toLowerCase();
    return tasks.filter((t) => {
      if (statusFilter !== "all" && t.status !== statusFilter) return false;
      if (!q) return true;
      return (
        t.title.toLowerCase().includes(q) ||
        (t.description || "").toLowerCase().includes(q)
      );
    });
  }, [tasks, statusFilter, search]);

  // Returns an object with one message per invalid field (empty object = form is valid)
  function validateForm(): FormErrors {
    const errs: FormErrors = {};
    const t = title.trim();
    if (!t) errs.title = "Task title is required";
    else if (t.length < 3) errs.title = "Title must be at least 3 characters";
    else if (t.length > 100) errs.title = "Title must be 100 characters or fewer";

    if (description.length > 500) errs.description = "Description must be 500 characters or fewer";

    if (dueDate && dueDate < todayString()) errs.dueDate = "Due date cannot be in the past";
    return errs;
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError("");

    const errs = validateForm();
    setFormErrors(errs);
    if (Object.keys(errs).length > 0) return; // stop here if anything is invalid

    setSubmitting(true);
    try {
      await apiFetch("/api/tasks", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          assigned_to: assignedTo,
          priority,
          due_date: dueDate,
        }),
      });
      setTitle("");
      setDescription("");
      setAssignedTo("");
      setPriority("medium");
      setDueDate("");
      setFormErrors({});
      setShowForm(false);
      loadTasks();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleComplete(id: string) {
    try {
      await apiFetch(`/api/tasks/${id}/complete`, { method: "PATCH" });
      loadTasks();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Delete this task?")) return;
    try {
      await apiFetch(`/api/tasks/${id}`, { method: "DELETE" });
      loadTasks();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function logout() {
    localStorage.removeItem("token");
    router.replace("/login");
  }

  const statCards = [
    { label: "Total", value: stats.total, color: "text-slate-900" },
    { label: "Pending", value: stats.pending, color: "text-blue-600" },
    { label: "Completed", value: stats.completed, color: "text-emerald-600" },
    { label: "Overdue", value: stats.overdue, color: "text-red-600" },
  ];

  const inputClass =
    "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200";
  const errorInputClass =
    "w-full rounded-lg border border-red-400 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-red-500 focus:outline-none focus:ring-2 focus:ring-red-100";

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* Top bar */}
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
              T
            </div>
            <span className="text-lg font-semibold">TaskFlow</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium leading-tight">{me?.name || me?.email}</p>
              <p className="text-xs text-slate-500">{me?.email}</p>
            </div>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-blue-700">
              {initials(me?.name || me?.email)}
            </div>
            <button
              onClick={logout}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        <div>
          <h1 className="text-2xl font-bold">Hi, {me?.name || "there"} 👋</h1>
          <p className="text-sm text-slate-500">Here is what is on your plate.</p>
        </div>

        {error && (
          <div className="flex items-start justify-between rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <span>{error}</span>
            <button onClick={() => setError("")} className="ml-4 font-medium underline">
              Dismiss
            </button>
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {statCards.map((s) => (
            <div key={s.label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{s.label}</p>
              <p className={`mt-1 text-3xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>

        {/* Toolbar */}
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1">
            {(["assigned", "created"] as View[]).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`rounded-md px-4 py-1.5 text-sm font-medium ${
                  view === v ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {v === "assigned" ? "Assigned to me" : "Created by me"}
              </button>
            ))}
          </div>
          <div className="flex flex-1 gap-2 md:max-w-md">
            <input
              className={inputClass}
              placeholder="Search tasks..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              className={`${inputClass} w-auto`}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            >
              <option value="all">All</option>
              <option value="pending">Pending</option>
              <option value="completed">Completed</option>
            </select>
          </div>
          <button
            onClick={() => {
              setShowForm((s) => !s);
              setFormErrors({});
            }}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            {showForm ? "Close" : "+ New task"}
          </button>
        </div>

        {/* Create form (noValidate turns off the browser popups so our own messages show) */}
        {showForm && (
          <form
            onSubmit={handleCreate}
            noValidate
            className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <h2 className="font-semibold">Create task</h2>

            <div>
              <input
                className={formErrors.title ? errorInputClass : inputClass}
                placeholder="Title"
                value={title}
                maxLength={120}
                onChange={(e) => {
                  setTitle(e.target.value);
                  if (formErrors.title) setFormErrors((f) => ({ ...f, title: undefined }));
                }}
                aria-invalid={!!formErrors.title}
              />
              {formErrors.title && <p className="mt-1 text-xs text-red-600">{formErrors.title}</p>}
            </div>

            <div>
              <textarea
                className={formErrors.description ? errorInputClass : inputClass}
                rows={3}
                placeholder="Description (optional)"
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  if (formErrors.description) setFormErrors((f) => ({ ...f, description: undefined }));
                }}
                aria-invalid={!!formErrors.description}
              />
              <div className="mt-1 flex justify-between text-xs">
                <span className="text-red-600">{formErrors.description}</span>
                <span className={description.length > 500 ? "text-red-600" : "text-slate-400"}>
                  {description.length}/500
                </span>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Assign to</label>
                <select className={inputClass} value={assignedTo} onChange={(e) => setAssignedTo(e.target.value)}>
                  <option value="">Unassigned</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name || u.email}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-slate-500">Only people who have signed in once appear here.</p>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Priority</label>
                <select className={inputClass} value={priority} onChange={(e) => setPriority(e.target.value)}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Due date</label>
                <input
                  type="date"
                  className={formErrors.dueDate ? errorInputClass : inputClass}
                  value={dueDate}
                  min={todayString()}
                  onChange={(e) => {
                    setDueDate(e.target.value);
                    if (formErrors.dueDate) setFormErrors((f) => ({ ...f, dueDate: undefined }));
                  }}
                  aria-invalid={!!formErrors.dueDate}
                />
                {formErrors.dueDate && <p className="mt-1 text-xs text-red-600">{formErrors.dueDate}</p>}
              </div>
            </div>

            <button
              disabled={submitting}
              className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
            >
              {submitting ? "Creating..." : "Add task"}
            </button>
          </form>
        )}

        {/* Task list */}
        {loading ? (
          <div className="grid gap-4 md:grid-cols-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-36 animate-pulse rounded-xl bg-slate-200" />
            ))}
          </div>
        ) : visibleTasks.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white py-16 text-center">
            <p className="text-lg font-medium">No tasks here yet</p>
            <p className="mt-1 text-sm text-slate-500">
              {search || statusFilter !== "all"
                ? "Try changing your search or filter."
                : 'Click "+ New task" to create one.'}
            </p>
          </div>
        ) : (
          <ul className="grid gap-4 md:grid-cols-2">
            {visibleTasks.map((t) => {
              const overdue = isOverdue(t);
              const done = t.status === "completed";
              return (
                <li
                  key={t.id}
                  className={`flex flex-col rounded-xl border border-l-4 border-slate-200 bg-white p-4 shadow-sm ${
                    PRIORITY_BORDER[t.priority] || "border-l-slate-300"
                  } ${done ? "opacity-70" : ""}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className={`font-semibold ${done ? "text-slate-500 line-through" : ""}`}>{t.title}</h3>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium uppercase ring-1 ring-inset ${
                        PRIORITY_STYLES[t.priority] || ""
                      }`}
                    >
                      {t.priority}
                    </span>
                  </div>

                  {t.description && (
                    <p className="mt-1 line-clamp-2 text-sm text-slate-600">{t.description}</p>
                  )}

                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                    <span className="flex items-center gap-1">
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-200 text-[10px] font-semibold">
                        {initials(t.assignee?.name || t.assignee?.email)}
                      </span>
                      {t.assignee?.name || t.assignee?.email || "Unassigned"}
                    </span>
                    <span className="text-slate-300">•</span>
                    <span>From {t.creator?.name || t.creator?.email}</span>
                    {t.due_date && (
                      <span
                        className={`rounded px-1.5 py-0.5 font-medium ${
                          overdue ? "bg-red-50 text-red-700" : "bg-slate-100"
                        }`}
                      >
                        {overdue ? "Overdue · " : "Due "}
                        {t.due_date}
                      </span>
                    )}
                    <span
                      className={`rounded px-1.5 py-0.5 font-medium ${
                        done ? "bg-emerald-50 text-emerald-700" : "bg-blue-50 text-blue-700"
                      }`}
                    >
                      {done ? "Completed" : "Pending"}
                    </span>
                  </div>

                  <div className="mt-4 flex gap-3 border-t border-slate-100 pt-3 text-sm">
                    {t.status === "pending" && (
                      <button
                        onClick={() => handleComplete(t.id)}
                        className="font-medium text-emerald-700 hover:underline"
                      >
                        ✓ Mark complete
                      </button>
                    )}
                    {t.created_by === me?.id && (
                      <button
                        onClick={() => handleDelete(t.id)}
                        className="font-medium text-red-600 hover:underline"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </main>
    </div>
  );
}