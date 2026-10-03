create extension if not exists "pgcrypto";

create table users (
  id uuid primary key default gen_random_uuid(),
  google_id text unique not null,
  email text unique not null,
  name text,
  picture text,
  created_at timestamptz default now()
);

create table tasks (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text,
  status text not null default 'pending' check (status in ('pending','completed')),
  priority text not null default 'medium' check (priority in ('low','medium','high')),
  due_date date,
  created_by uuid not null references users(id) on delete cascade,
  assigned_to uuid references users(id) on delete set null,
  created_at timestamptz default now(),
  completed_at timestamptz
);

create index idx_tasks_assigned_to on tasks(assigned_to);
create index idx_tasks_created_by on tasks(created_by);

-- Block direct public access; the Flask backend uses the service key, which bypasses RLS
alter table users enable row level security;
alter table tasks enable row level security;