-- Create a new schema named s3dmap
CREATE SCHEMA s3dmap;
-- Create a table named inventory within the s3dmap schema
CREATE TABLE inventory (
    bucket TEXT,
    suffix TEXT,
    depth int,
    key TEXT DEFAULT NULL,
    version_id TEXT,
    is_latest BOOLEAN,
    is_delete_marker BOOLEAN,
    size bigint,
    last_modified_date TIMESTAMP,
    e_tag TEXT,
    storage_class TEXT,
    is_multipart_uploaded BOOLEAN,
    replication_status TEXT,
    encryption_status TEXT,
    object_lock_retain_until_date TEXT,
    object_lock_mode TEXT,
    object_lock_legal_hold_status TEXT,
    intelligent_tiering_access_tier TEXT,
    bucket_key_status TEXT,
    checksum_algorithm TEXT,
    object_access_control_list TEXT,
    object_owner TEXT
);
CREATE OR REPLACE FUNCTION get_subpaths(input_path TEXT) RETURNS TABLE(subpath TEXT) AS $$
DECLARE path_parts TEXT [];
-- Array to hold the split parts of the input path
current_path TEXT;
-- Variable to accumulate the path parts
BEGIN -- Handle NULL or empty string input
IF input_path IS NULL
OR input_path = '' THEN subpath := '';
-- Return an empty string
RETURN NEXT;
RETURN;
END IF;
path_parts := string_to_array(input_path, '/');
-- Split the input path by '/'
current_path := '';
-- Initialize the current path
-- Loop through each part of the path to build up the subpaths
FOR i IN 1..array_length(path_parts, 1) LOOP -- Skip empty parts to avoid double slashes or leading slash issues
IF path_parts [i] <> '' THEN -- Check if the current path is empty to avoid a leading '/'
IF current_path = '' THEN current_path := path_parts [i];
-- Start with the first non-empty part
ELSE current_path := current_path || '/' || path_parts [i];
-- Subsequent parts
END IF;
subpath := current_path;
-- Output the current subpath
RETURN NEXT;
END IF;
END LOOP;
END;
$$ LANGUAGE plpgsql;
CREATE OR REPLACE FUNCTION get_depth(input_string TEXT) RETURNS INTEGER AS $$ BEGIN RETURN LENGTH(input_string) - LENGTH(REPLACE(input_string, '/', '')) + 1;
END;
$$ LANGUAGE plpgsql;
create MATERIALIZED view inventory_flatten as
select
	case
		when sp.subpath <> '' then sp.subpath
		else '__BUCKET_ROOT__'
	end as prefix,
	i.*
from inventory i,
	get_subpaths(i.key) sp
where 1=1
	and i.size != 0
	and i.key != sp.subpath;


create MATERIALIZED view prefixes as 
select bucket,
    prefix,
    min(get_depth(prefix)) as depth,
    -- keys
    count(distinct key) as count_distinct_key,
    -- depth
    max(depth) as max_depth,
    round(avg(depth)) as avg_depth,
    -- size
    max(size) as max_size,
    min(size) as min_size,
    round(avg(size)) as avg_size,
    sum(size) as sum_size,
    -- suffix
    count(distinct suffix) as count_distinct_suffix,
    array_agg(distinct suffix) as distinct_suffix,
    -- storage_class
    count(distinct storage_class) as count_distinct_storage_class,
    array_agg(distinct storage_class) as distinct_storage_class,
    count(
        case
            when storage_class = 'INTELLIGENT_TIERING' then 1
            else null
        end
    ) > 0 as is_intt,
    case
        when count(distinct key) = 0 then 0
        else count(
            case
                when storage_class = 'INTELLIGENT_TIERING' then 1
                else null
            end
        ) / count(distinct key)
    end as ratio_intt_coverage_count,
    case
        when sum(size) = 0 then 0
        else sum(
            case
                when storage_class = 'INTELLIGENT_TIERING' then size
                else 0
            end
        ) / sum(size)
    end as ratio_intt_coverage_size,
    -- versions
    count(
        case
            when not is_latest then 1
            else null
        end
    ) > 0 as is_version,
    count(
        case
            when not is_latest then 1
            else null
        end
    ) as count_version,
    case
        when count(distinct key) = 0 then 0
        else count(
            case
                when not is_latest then 1
                else null
            end
        ) / count(distinct key)
    end as ratio_version_latest_count,
    case
        when sum(size) = 0 then 0
        else sum(
            case
                when not is_latest then size
                else 0
            end
        ) / sum(size)
    end as ratio_version_latest_size,
    -- last_modified_date
    max(last_modified_date) as max_last_modified_date,
    extract(
        DAYS
        FROM CURRENT_DATE - max(last_modified_date)
    ) as max_days_since_last_modified,
    min(last_modified_date) as min_last_modified_date,
    extract(
        DAYS
        FROM CURRENT_DATE - min(last_modified_date)
    ) as min_days_since_last_modified,
    round(
        avg(
            extract(
                DAY
                FROM CURRENT_DATE - last_modified_date
            )
        )
    ) as avg_days_since_last_modified,
    -- object_owner
    count(distinct object_owner) as count_distinct_owner,
    array_agg(distinct object_owner) as distinct_owner -- encryption
    -- replication
from inventory_flatten
group by 1,
    2;

CREATE TABLE IF NOT EXISTS prefixes_demo
(
    bucket text COLLATE pg_catalog."default",
    prefix text COLLATE pg_catalog."default",
    depth integer,
    count_distinct_key bigint,
    max_depth integer,
    avg_depth numeric,
    max_size bigint,
    min_size bigint,
    avg_size numeric,
    sum_size numeric,
    count_distinct_suffix bigint,
    distinct_suffix text[] COLLATE pg_catalog."default",
    count_distinct_storage_class bigint,
    distinct_storage_class text[] COLLATE pg_catalog."default",
    is_intt boolean,
    ratio_intt_coverage_count bigint,
    ratio_intt_coverage_size numeric,
    is_version boolean,
    count_version bigint,
    ratio_version_latest_count bigint,
    ratio_version_latest_size numeric,
    max_last_modified_date timestamp without time zone,
    max_days_since_last_modified numeric,
    min_last_modified_date timestamp without time zone,
    min_days_since_last_modified numeric,
    avg_days_since_last_modified numeric,
    count_distinct_owner bigint,
    distinct_owner text[] COLLATE pg_catalog."default"
);

COPY prefixes_demo FROM '/docker-entrypoint-initdb.d/prefixes_demo_sample-bucket.csv' CSV HEADER;