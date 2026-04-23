create table if not exists public.broker_connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  account_id text not null unique,
  provider text not null default 'oanda',
  broker_account_id text not null,
  api_key_encrypted text not null,
  environment text not null default 'practice',
  created_at timestamptz not null default now()
);

create table if not exists public.risk_limits (
  id uuid primary key default gen_random_uuid(),
  account_id text not null unique,
  max_daily_loss numeric not null default 100,
  max_open_trades int not null default 3,
  max_position_size numeric not null default 1000,
  allowed_instruments jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.strategy_runs (
  id uuid primary key default gen_random_uuid(),
  account_id text not null,
  strategy text not null,
  status text not null default 'running',
  created_at timestamptz not null default now()
);

create table if not exists public.orders (
  id uuid primary key default gen_random_uuid(),
  account_id text not null,
  strategy text not null,
  side text not null,
  symbol text not null,
  request_payload jsonb not null default '{}'::jsonb,
  broker_result jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.broker_connections enable row level security;
alter table public.risk_limits enable row level security;
alter table public.strategy_runs enable row level security;
alter table public.orders enable row level security;

drop policy if exists "broker_connections_owner_select" on public.broker_connections;
create policy "broker_connections_owner_select" on public.broker_connections
for select using (auth.uid() = user_id);

drop policy if exists "broker_connections_owner_write" on public.broker_connections;
create policy "broker_connections_owner_write" on public.broker_connections
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "risk_limits_owner" on public.risk_limits;
create policy "risk_limits_owner" on public.risk_limits
for all using (
  exists (
    select 1 from public.broker_connections bc
    where bc.account_id = risk_limits.account_id
    and bc.user_id = auth.uid()
  )
) with check (
  exists (
    select 1 from public.broker_connections bc
    where bc.account_id = risk_limits.account_id
    and bc.user_id = auth.uid()
  )
);

drop policy if exists "strategy_runs_owner" on public.strategy_runs;
create policy "strategy_runs_owner" on public.strategy_runs
for all using (
  exists (
    select 1 from public.broker_connections bc
    where bc.account_id = strategy_runs.account_id
    and bc.user_id = auth.uid()
  )
) with check (
  exists (
    select 1 from public.broker_connections bc
    where bc.account_id = strategy_runs.account_id
    and bc.user_id = auth.uid()
  )
);

drop policy if exists "orders_owner" on public.orders;
create policy "orders_owner" on public.orders
for all using (
  exists (
    select 1 from public.broker_connections bc
    where bc.account_id = orders.account_id
    and bc.user_id = auth.uid()
  )
) with check (
  exists (
    select 1 from public.broker_connections bc
    where bc.account_id = orders.account_id
    and bc.user_id = auth.uid()
  )
);
