-- Run once in the Supabase SQL editor. Access goes through the Vercel server only.
create table public.photos (
  id text primary key, owner_id text not null, name text not null,
  path text not null unique, created_at timestamptz not null default now()
);
create table public.drinks (
  id uuid primary key default gen_random_uuid(), owner_id text not null,
  kind text not null check(kind in ('coffee','beer','wine')),
  created_at timestamptz not null default now()
);
create index drinks_owner_time on public.drinks(owner_id,created_at desc);
create table public.event_limits (
  owner_id text primary key, upload_at timestamptz,
  login_start timestamptz, login_count integer not null default 0
);
alter table public.photos enable row level security;
alter table public.drinks enable row level security;
alter table public.event_limits enable row level security;
revoke all on public.photos,public.drinks,public.event_limits from anon,authenticated;
grant all on public.photos,public.drinks,public.event_limits to service_role;

create function public.drink_totals() returns jsonb language sql stable set search_path=public as $$
  select jsonb_build_object('coffee',count(*) filter(where kind='coffee'),
    'beer',count(*) filter(where kind='beer'),'wine',count(*) filter(where kind='wine')) from drinks;
$$;
create function public.log_drink(p_owner text,p_kind text) returns jsonb language plpgsql set search_path=public as $$
declare new_id uuid;
begin
  perform pg_advisory_xact_lock(hashtextextended(p_owner,0));
  if exists(select 1 from drinks where owner_id=p_owner and created_at>now()-interval '30 seconds') then
    return '{}'::jsonb;
  end if;
  insert into drinks(owner_id,kind) values(p_owner,p_kind) returning id into new_id;
  return jsonb_build_object('id',new_id);
end; $$;
create function public.claim_upload(p_owner text) returns boolean language plpgsql set search_path=public as $$
declare claimed text;
begin
  insert into event_limits(owner_id,upload_at) values(p_owner,now())
  on conflict(owner_id) do update set upload_at=now()
  where event_limits.upload_at is null or event_limits.upload_at<now()-interval '10 seconds'
  returning owner_id into claimed;
  return claimed is not null;
end; $$;
create function public.allow_login(p_owner text) returns boolean language plpgsql set search_path=public as $$
declare attempts integer;
begin
  insert into event_limits(owner_id,login_start,login_count) values(p_owner,now(),1)
  on conflict(owner_id) do update set
    login_count=case when event_limits.login_start<now()-interval '15 minutes' then 1 else event_limits.login_count+1 end,
    login_start=case when event_limits.login_start<now()-interval '15 minutes' then now() else event_limits.login_start end
  returning login_count into attempts;
  return attempts<=30;
end; $$;
revoke execute on function public.drink_totals(),public.log_drink(text,text),public.claim_upload(text),public.allow_login(text) from public,anon,authenticated;
grant execute on function public.drink_totals(),public.log_drink(text,text),public.claim_upload(text),public.allow_login(text) to service_role;
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values('summit-photos','summit-photos',false,2500000,array['image/jpeg']);
