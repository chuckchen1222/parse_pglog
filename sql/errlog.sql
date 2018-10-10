--
-- PostgreSQL database dump
--

-- Dumped from database version 10.3
-- Dumped by pg_dump version 10.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


--
-- Name: db_log_level; Type: TYPE; Schema: public; Owner: dbadmin
--

CREATE TYPE public.db_log_level AS ENUM (
    'WARNING',
    'ERROR',
    'FATAL',
    'PANIC'
);


ALTER TYPE public.db_log_level OWNER TO dbadmin;

--
-- Name: db_err_log_seq; Type: SEQUENCE; Schema: public; Owner: dbadmin
--

CREATE SEQUENCE public.db_err_log_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.db_err_log_seq OWNER TO dbadmin;

--
-- Name: db_err_send_seq; Type: SEQUENCE; Schema: public; Owner: dbadmin
--

CREATE SEQUENCE public.db_err_send_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.db_err_send_seq OWNER TO dbadmin;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: t_db_err_log; Type: TABLE; Schema: public; Owner: dbadmin
--

CREATE TABLE public.t_db_err_log (
    id integer DEFAULT nextval('public.db_err_log_seq'::regclass) NOT NULL,
    err_date date NOT NULL,
    hostname character varying(50) NOT NULL,
    err_time timestamp without time zone NOT NULL,
    db_user character varying(50) NOT NULL,
    db_name character varying(50) NOT NULL,
    client_addr character varying(50) NOT NULL,
    log_level public.db_log_level NOT NULL,
    err_log character varying NOT NULL
);


ALTER TABLE public.t_db_err_log OWNER TO dbadmin;

--
-- Name: t_db_err_log_history; Type: TABLE; Schema: public; Owner: dbadmin
--

CREATE TABLE public.t_db_err_log_history (
    id integer,
    err_date date,
    hostname character varying(50),
    err_time timestamp without time zone,
    db_user character varying(50),
    db_name character varying(50),
    client_addr character varying(50),
    log_level public.db_log_level,
    err_log character varying
);


ALTER TABLE public.t_db_err_log_history OWNER TO dbadmin;

--
-- Name: t_db_err_send; Type: TABLE; Schema: public; Owner: dbadmin
--

CREATE TABLE public.t_db_err_send (
    id integer DEFAULT nextval('public.db_err_send_seq'::regclass) NOT NULL,
    err_date date NOT NULL,
    hostname character varying(50) NOT NULL,
    err_count integer NOT NULL,
    err_log character varying NOT NULL,
    is_sent boolean DEFAULT false NOT NULL,
    sent_times timestamp without time zone,
    is_handle boolean DEFAULT true NOT NULL,
    db_name character varying(50),
    client_addr character varying(50)
);


ALTER TABLE public.t_db_err_send OWNER TO dbadmin;

--
-- Name: t_db_err_send_history; Type: TABLE; Schema: public; Owner: dbadmin
--

CREATE TABLE public.t_db_err_send_history (
    id integer,
    err_date date,
    hostname character varying(50),
    err_count integer,
    err_log character varying,
    is_sent boolean,
    sent_times timestamp without time zone,
    is_handle boolean,
    db_name character varying(50),
    client_addr character varying(50)
);


ALTER TABLE public.t_db_err_send_history OWNER TO dbadmin;

--
-- Name: t_db_err_log t_db_err_log_pkey; Type: CONSTRAINT; Schema: public; Owner: dbadmin
--

ALTER TABLE ONLY public.t_db_err_log
    ADD CONSTRAINT t_db_err_log_pkey PRIMARY KEY (id);


--
-- Name: t_db_err_send t_db_err_send_pkey; Type: CONSTRAINT; Schema: public; Owner: dbadmin
--

ALTER TABLE ONLY public.t_db_err_send
    ADD CONSTRAINT t_db_err_send_pkey PRIMARY KEY (id);


--
-- Name: idx_db_err_log_01; Type: INDEX; Schema: public; Owner: dbadmin
--

CREATE INDEX idx_db_err_log_01 ON public.t_db_err_log USING btree (hostname, err_date);


--
-- Name: idx_db_err_log_02; Type: INDEX; Schema: public; Owner: dbadmin
--

CREATE INDEX idx_db_err_log_02 ON public.t_db_err_log USING btree (hostname, err_date, err_log);


--
-- Name: uidx_db_err_send_01; Type: INDEX; Schema: public; Owner: dbadmin
--

CREATE UNIQUE INDEX uidx_db_err_send_01 ON public.t_db_err_send USING btree (err_date, hostname, err_log);


--
-- PostgreSQL database dump complete
--

