-- Mission registry for the "Mission context" feature.
--
-- Stores where each mission leg departs from and where it is heading. The
-- craft's current position is NOT stored: the API resolves it live (NASA ISS
-- OEM while docked). Departure and destination are filled once, from Launch
-- Library 2 (LL2) when it has the data and by hand otherwise, so requests do
-- not depend on LL2 (free plan: a few calls per hour).

-- A point a leg departs from or heads to.
--   tracked: a moving object resolved live by the API (today only the ISS).
--   fixed:   a coordinate, e.g. a launch pad or a splashdown zone.
create table public.mission_places (
  id uuid primary key default gen_random_uuid(),
  code text not null unique check (code ~ '^[a-z0-9_]+$'),
  name text not null check (btrim(name) <> ''),
  label text not null check (btrim(label) <> ''),
  kind text not null check (kind in ('tracked', 'fixed')),
  tracked_object text check (tracked_object in ('iss')),
  latitude double precision check (latitude between -90 and 90),
  longitude double precision check (longitude between -180 and 180),
  -- Origin of a fixed coordinate; tracked places are resolved live.
  source text check (source in ('ll2', 'mission_registration', 'manual')),
  simulated boolean not null default false,
  source_url text,
  fetched_at timestamptz,

  constraint mission_places_kind_shape_check check (
    (kind = 'tracked' and tracked_object is not null
      and latitude is null and longitude is null and source is null)
    or (kind = 'fixed' and tracked_object is null
      and latitude is not null and longitude is not null and source is not null)
  )
);

create table public.missions (
  id uuid primary key default gen_random_uuid(),
  code text not null unique check (code ~ '^[a-z0-9-]+$'),
  name text not null check (btrim(name) <> ''),
  -- Mission used by sessions without their own link (the fictional astronaut).
  is_demo boolean not null default false,
  ll2_launch_id uuid,
  -- NORAD catalog number of the free-flying craft, for future CelesTrak/SGP4 use.
  norad_id integer check (norad_id > 0),
  reference_label text,
  reference_url text,
  created_at timestamptz not null default now()
);

-- At most one demo mission.
create unique index missions_single_demo_idx on public.missions (is_demo) where is_demo;

-- One row per phase shown by GET /api/mission-context?phase=...
create table public.mission_legs (
  mission_id uuid not null references public.missions(id) on delete cascade,
  phase text not null check (phase in ('in_orbit', 'return_to_earth')),
  departure_place_id uuid not null references public.mission_places(id),
  departure_at timestamptz,
  departure_at_source text check (departure_at_source in ('ll2', 'mission_registration', 'manual', 'simulated')),
  destination_place_id uuid not null references public.mission_places(id),
  destination_description text not null check (btrim(destination_description) <> ''),

  primary key (mission_id, phase),
  constraint mission_legs_distinct_places_check check (departure_place_id <> destination_place_id),
  constraint mission_legs_departure_source_check check ((departure_at is null) = (departure_at_source is null))
);

create index mission_legs_departure_place_idx on public.mission_legs (departure_place_id);
create index mission_legs_destination_place_idx on public.mission_legs (destination_place_id);

-- Links a demo session (signed mittus_session cookie) to its mission.
-- session_id is the primary key: a session has exactly one mission.
create table public.session_missions (
  session_id uuid primary key,
  mission_id uuid not null references public.missions(id) on delete cascade,
  created_at timestamptz not null default now()
);

create index session_missions_mission_idx on public.session_missions (mission_id);

-- Server-only access, like the other tables: RLS on, no policies, and no
-- grants for the public API roles.
alter table public.mission_places enable row level security;
alter table public.missions enable row level security;
alter table public.mission_legs enable row level security;
alter table public.session_missions enable row level security;
revoke all on table public.mission_places, public.missions, public.mission_legs, public.session_missions
  from public, anon, authenticated;

-- Demo mission, modeled on NASA's SpaceX Crew-12 (launch data from LL2).
insert into public.mission_places
  (code, name, label, kind, tracked_object, latitude, longitude, source, simulated, source_url, fetched_at)
values
  ('cape_canaveral_slc_40', 'Cape Canaveral', 'Space Launch Complex 40, Cape Canaveral SFS, FL, USA',
    'fixed', null, 28.56194122, -80.57735736, 'll2', false,
    'https://ll.thespacedevs.com/2.3.0/launches/862b54e3-7bf8-48e5-8cd1-d77257d5fde9/', '2026-11-14T22:00:00Z'),
  ('iss', 'International Space Station', 'International Space Station',
    'tracked', 'iss', null, null, null, false, null, null),
  ('pacific_splashdown_california', 'Earth', 'Pacific splashdown zone off California',
    'fixed', null, 32.6, -118.2, 'manual', true, null, null);

insert into public.missions (code, name, is_demo, ll2_launch_id, reference_label, reference_url)
values ('demo-crew-12', 'Mittus demo mission', true, '862b54e3-7bf8-48e5-8cd1-d77257d5fde9',
  'NASA SpaceX Crew-12 mission profile', 'https://www.nasa.gov/mission/nasas-spacex-crew-12/');

insert into public.mission_legs
  (mission_id, phase, departure_place_id, departure_at, departure_at_source, destination_place_id, destination_description)
select m.id, l.phase, dep.id, l.departure_at, l.departure_at_source, dst.id, l.destination_description
from public.missions m
cross join (values
  ('in_orbit', 'cape_canaveral_slc_40', '2026-02-13T10:15:56Z'::timestamptz, 'll2', 'iss',
    'Crew Dragon flew to the ISS and stays docked while the crew lives aboard.'),
  ('return_to_earth', 'iss', null::timestamptz, null, 'pacific_splashdown_california',
    'Crew Dragon brings the crew back to a splashdown zone in the ocean.')
) as l(phase, departure_code, departure_at, departure_at_source, destination_code, destination_description)
join public.mission_places dep on dep.code = l.departure_code
join public.mission_places dst on dst.code = l.destination_code
where m.code = 'demo-crew-12';
