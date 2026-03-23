--
-- PostgreSQL database dump
--

\restrict oAMIccKOZXFJaflO4Euu2oDltqkGDfeE6gQzmJfS3Sxrejml3ImI6eahqjxCuP5

-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: test; Type: TABLE; Schema: public; Owner: arco_user
--

CREATE TABLE public.test (
    id integer,
    name text
);


ALTER TABLE public.test OWNER TO arco_user;

--
-- PostgreSQL database dump complete
--

\unrestrict oAMIccKOZXFJaflO4Euu2oDltqkGDfeE6gQzmJfS3Sxrejml3ImI6eahqjxCuP5

