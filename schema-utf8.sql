--
-- PostgreSQL database dump
--

\restrict cCDW9K3hulwT0HOVlycmHepRFwRxalireNPlGAgNKTkmNYJkQSZwfeScDbf20Xd

-- Dumped from database version 17.6 (Debian 17.6-1.pgdg13+1)
-- Dumped by pg_dump version 17.6 (Debian 17.6-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: company_data_source_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.company_data_source_enum AS ENUM (
    'funding',
    'hiring',
    'event'
);


--
-- Name: contacted_status_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.contacted_status_enum AS ENUM (
    'uncontacted',
    'contacted',
    'pending',
    'requested',
    'engaged',
    'failed',
    'opted_out'
);


--
-- Name: status_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.status_enum AS ENUM (
    'lead',
    'mql',
    'sql',
    'contacted',
    'converted',
    'disqualified'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: companies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.companies (
    id integer NOT NULL,
    apollo_id text,
    name text,
    website_url text,
    linkedin_url text,
    phone text,
    founded_year integer,
    market_cap numeric,
    annual_revenue numeric,
    industries text[],
    estimated_num_employees integer,
    keywords text[],
    organization_headcount_six_month_growth numeric,
    organization_headcount_twelve_month_growth numeric,
    city text,
    state text,
    country text,
    short_description text,
    total_funding numeric,
    technology_names text[],
    icp_score numeric(4,1),
    contacted_status public.contacted_status_enum DEFAULT 'uncontacted'::public.contacted_status_enum,
    notes text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    company_data_source public.company_data_source_enum,
    status public.status_enum DEFAULT 'lead'::public.status_enum NOT NULL,
    latest_funding_round text,
    latest_funding_amount numeric,
    latest_funding_currency text,
    source_link text,
    contacted_status_precedence integer,
    specific_tasks_and_scores jsonb
);


--
-- Name: companies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.companies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: companies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.companies_id_seq OWNED BY public.companies.id;


--
-- Name: emails_sent; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.emails_sent (
    id integer NOT NULL,
    recipient_id integer NOT NULL,
    company_id integer NOT NULL,
    subject text NOT NULL,
    body text NOT NULL,
    status public.contacted_status_enum DEFAULT 'pending'::public.contacted_status_enum NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    sent_at timestamp without time zone,
    sequence_number integer NOT NULL,
    CONSTRAINT sequence_number_range CHECK (((sequence_number >= 1) AND (sequence_number <= 4)))
);


--
-- Name: emails_sent_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.emails_sent_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: emails_sent_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.emails_sent_id_seq OWNED BY public.emails_sent.id;


--
-- Name: icp_scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.icp_scores (
    id integer NOT NULL,
    company_id integer NOT NULL,
    age_score numeric(5,2),
    employee_count_score numeric(5,2),
    funding_stage_score numeric(5,2),
    keyword_score numeric(5,2),
    contactability_score numeric(5,2),
    geography_score numeric(5,2),
    total_score numeric(4,1) NOT NULL,
    category_breakdown jsonb,
    top_matches jsonb,
    interpretation text,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: icp_scores_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.icp_scores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: icp_scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.icp_scores_id_seq OWNED BY public.icp_scores.id;


--
-- Name: normalized_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.normalized_events (
    id integer NOT NULL,
    master_id integer NOT NULL,
    event_id text,
    event_summary text,
    event_is_online boolean,
    event_organizer_id character varying,
    company_name text
);


--
-- Name: normalized_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.normalized_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: normalized_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.normalized_events_id_seq OWNED BY public.normalized_events.id;


--
-- Name: normalized_funding; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.normalized_funding (
    id integer NOT NULL,
    master_id integer,
    company_name text,
    company_decision_makers text[],
    company_decision_makers_position text[],
    funding_round text,
    amount_raised numeric,
    currency text,
    investor_companies text[],
    investor_people text[]
);


--
-- Name: normalized_funding_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.normalized_funding_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: normalized_funding_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.normalized_funding_id_seq OWNED BY public.normalized_funding.id;


--
-- Name: normalized_hiring; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.normalized_hiring (
    id integer NOT NULL,
    master_id integer NOT NULL,
    company_name text,
    company_decision_makers text[],
    company_decision_makers_position text[],
    job_roles text[],
    hiring_reasons text[]
);


--
-- Name: normalized_hiring_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.normalized_hiring_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: normalized_hiring_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.normalized_hiring_id_seq OWNED BY public.normalized_hiring.id;


--
-- Name: normalized_master; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.normalized_master (
    id integer NOT NULL,
    type public.company_data_source_enum,
    source text,
    link text,
    title text,
    created_at timestamp with time zone DEFAULT now(),
    city text,
    country text,
    tags text[]
);


--
-- Name: normalized_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.normalized_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: normalized_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.normalized_id_seq OWNED BY public.normalized_master.id;


--
-- Name: people; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.people (
    id bigint NOT NULL,
    apollo_id text NOT NULL,
    first_name text,
    last_name text,
    full_name text,
    linkedin_url text,
    title text,
    email_status text,
    headline text,
    organization_id text,
    seniority text,
    departments text[],
    subdepartments text[],
    functions text[],
    email text,
    number text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    contacted_status public.contacted_status_enum DEFAULT 'uncontacted'::public.contacted_status_enum,
    notes text,
    contacted_status_precedence integer,
    times_contacted integer DEFAULT 0 NOT NULL,
    last_contacted_at timestamp with time zone,
    subscribed boolean DEFAULT true NOT NULL,
    has_replied boolean DEFAULT false NOT NULL,
    CONSTRAINT times_contacted_range CHECK (((times_contacted >= 0) AND (times_contacted <= 4)))
);


--
-- Name: people_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.people_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: people_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.people_id_seq OWNED BY public.people.id;


--
-- Name: companies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.companies ALTER COLUMN id SET DEFAULT nextval('public.companies_id_seq'::regclass);


--
-- Name: emails_sent id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.emails_sent ALTER COLUMN id SET DEFAULT nextval('public.emails_sent_id_seq'::regclass);


--
-- Name: icp_scores id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.icp_scores ALTER COLUMN id SET DEFAULT nextval('public.icp_scores_id_seq'::regclass);


--
-- Name: normalized_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_events ALTER COLUMN id SET DEFAULT nextval('public.normalized_events_id_seq'::regclass);


--
-- Name: normalized_funding id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_funding ALTER COLUMN id SET DEFAULT nextval('public.normalized_funding_id_seq'::regclass);


--
-- Name: normalized_hiring id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_hiring ALTER COLUMN id SET DEFAULT nextval('public.normalized_hiring_id_seq'::regclass);


--
-- Name: normalized_master id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_master ALTER COLUMN id SET DEFAULT nextval('public.normalized_id_seq'::regclass);


--
-- Name: people id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people ALTER COLUMN id SET DEFAULT nextval('public.people_id_seq'::regclass);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);


--
-- Name: emails_sent emails_sent_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.emails_sent
    ADD CONSTRAINT emails_sent_pkey PRIMARY KEY (id);


--
-- Name: icp_scores icp_scores_company_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.icp_scores
    ADD CONSTRAINT icp_scores_company_id_key UNIQUE (company_id);


--
-- Name: icp_scores icp_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.icp_scores
    ADD CONSTRAINT icp_scores_pkey PRIMARY KEY (id);


--
-- Name: normalized_events normalized_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_events
    ADD CONSTRAINT normalized_events_pkey PRIMARY KEY (id);


--
-- Name: normalized_funding normalized_funding_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_funding
    ADD CONSTRAINT normalized_funding_pkey PRIMARY KEY (id);


--
-- Name: normalized_hiring normalized_hiring_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_hiring
    ADD CONSTRAINT normalized_hiring_pkey PRIMARY KEY (id);


--
-- Name: normalized_master normalized_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_master
    ADD CONSTRAINT normalized_pkey PRIMARY KEY (id);


--
-- Name: people people_apollo_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people
    ADD CONSTRAINT people_apollo_id_key UNIQUE (apollo_id);


--
-- Name: people people_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people
    ADD CONSTRAINT people_pkey PRIMARY KEY (id);


--
-- Name: companies unique_apollo_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT unique_apollo_id UNIQUE (apollo_id);


--
-- Name: normalized_master unique_link; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_master
    ADD CONSTRAINT unique_link UNIQUE (link);


--
-- Name: company_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX company_name ON public.companies USING btree (name);


--
-- Name: idx_icp_scores_company_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_icp_scores_company_id ON public.icp_scores USING btree (company_id);


--
-- Name: idx_people_drip; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_people_drip ON public.people USING btree (subscribed, has_replied, times_contacted, last_contacted_at);


--
-- Name: emails_sent emails_sent_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.emails_sent
    ADD CONSTRAINT emails_sent_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: emails_sent emails_sent_recipient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.emails_sent
    ADD CONSTRAINT emails_sent_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES public.people(id);


--
-- Name: icp_scores icp_scores_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.icp_scores
    ADD CONSTRAINT icp_scores_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: normalized_events normalized_events_normalization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_events
    ADD CONSTRAINT normalized_events_normalization_id_fkey FOREIGN KEY (master_id) REFERENCES public.normalized_master(id) ON DELETE CASCADE;


--
-- Name: normalized_funding normalized_funding_normalized_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_funding
    ADD CONSTRAINT normalized_funding_normalized_id_fkey FOREIGN KEY (master_id) REFERENCES public.normalized_master(id) ON DELETE CASCADE;


--
-- Name: normalized_hiring normalized_hiring_normalizaton_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_hiring
    ADD CONSTRAINT normalized_hiring_normalizaton_id_fkey FOREIGN KEY (master_id) REFERENCES public.normalized_master(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict cCDW9K3hulwT0HOVlycmHepRFwRxalireNPlGAgNKTkmNYJkQSZwfeScDbf20Xd

