CREATE SCHEMA IF NOT EXISTS fake;

CREATE TABLE IF NOT EXISTS fake.words (
    locale TEXT NOT NULL,
    category TEXT NOT NULL,
    position INTEGER NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (locale, category, position)
);

CREATE TABLE IF NOT EXISTS fake.word_counts (
    locale TEXT NOT NULL,
    category TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK (amount > 0),
    PRIMARY KEY (locale, category)
);

CREATE OR REPLACE PROCEDURE fake.uniform_value(
    IN p_locale TEXT, IN p_seed BIGINT, IN p_position BIGINT,
    IN p_channel TEXT, INOUT p_value DOUBLE PRECISION
)
LANGUAGE plpgsql AS $$
BEGIN
    p_value := (
        ('x' || substr(md5(concat_ws('|', p_locale, p_seed, p_position, p_channel)), 1, 13))::bit(52)::bigint
        + 0.5
    ) / 4503599627370496.0;
END;
$$;

CREATE OR REPLACE PROCEDURE fake.word(
    IN p_locale TEXT, IN p_category TEXT, IN p_seed BIGINT,
    IN p_position BIGINT, IN p_channel TEXT, INOUT p_value TEXT
)
LANGUAGE plpgsql AS $$
DECLARE
    v_amount INTEGER;
    v_random DOUBLE PRECISION;
BEGIN
    SELECT amount INTO STRICT v_amount
    FROM fake.word_counts
    WHERE locale = p_locale AND category = p_category;
    CALL fake.uniform_value(p_locale, p_seed, p_position, p_channel, v_random);
    SELECT value INTO STRICT p_value
    FROM fake.words
    WHERE locale = p_locale AND category = p_category
      AND position = floor(v_random * v_amount)::integer + 1;
END;
$$;

CREATE OR REPLACE PROCEDURE fake.normal_value(
    IN p_locale TEXT, IN p_seed BIGINT, IN p_position BIGINT,
    IN p_channel TEXT, IN p_mean DOUBLE PRECISION,
    IN p_deviation DOUBLE PRECISION, INOUT p_value DOUBLE PRECISION
)
LANGUAGE plpgsql AS $$
DECLARE
    v_u DOUBLE PRECISION;
    v_v DOUBLE PRECISION;
BEGIN
    IF p_deviation < 0 THEN
        RAISE EXCEPTION 'Standard deviation cannot be negative';
    END IF;
    CALL fake.uniform_value(p_locale, p_seed, p_position, p_channel || '.u', v_u);
    CALL fake.uniform_value(p_locale, p_seed, p_position, p_channel || '.v', v_v);
    p_value := p_mean + p_deviation * sqrt(-2 * ln(v_u)) * cos(2 * pi() * v_v);
END;
$$;

CREATE OR REPLACE PROCEDURE fake.contact(
    IN p_locale TEXT, IN p_seed BIGINT, IN p_position BIGINT,
    INOUT p_record JSONB
)
LANGUAGE plpgsql AS $$
DECLARE
    v_first TEXT;
    v_middle TEXT;
    v_last TEXT;
    v_title TEXT;
    v_street TEXT;
    v_suffix TEXT;
    v_city TEXT;
    v_state TEXT;
    v_eye TEXT;
    v_name TEXT;
    v_address TEXT;
    v_postcode TEXT;
    v_phone TEXT;
    v_email TEXT;
    v_house INTEGER;
    v_phone_part BIGINT;
    v_u DOUBLE PRECISION;
    v_v DOUBLE PRECISION;
    v_lat DOUBLE PRECISION;
    v_lon DOUBLE PRECISION;
    v_height DOUBLE PRECISION;
    v_weight DOUBLE PRECISION;
BEGIN
    CALL fake.word(p_locale, 'first', p_seed, p_position, 'first', v_first);
    CALL fake.word(p_locale, 'first', p_seed, p_position, 'middle', v_middle);
    CALL fake.word(p_locale, 'last', p_seed, p_position, 'last', v_last);
    CALL fake.word(p_locale, 'title', p_seed, p_position, 'title', v_title);
    CALL fake.uniform_value(p_locale, p_seed, p_position, 'middle.present', v_u);
    v_name := v_first || CASE WHEN v_u < 0.3 THEN ' ' || v_middle ELSE '' END || ' ' || v_last;
    CALL fake.uniform_value(p_locale, p_seed, p_position, 'title.present', v_u);
    IF v_u < 0.15 THEN
        v_name := v_title || ' ' || v_name;
    END IF;
    CALL fake.word(p_locale, 'street', p_seed, p_position, 'street', v_street);
    CALL fake.word(p_locale, 'suffix', p_seed, p_position, 'suffix', v_suffix);
    CALL fake.word(p_locale, 'city', p_seed, p_position, 'city', v_city);
    CALL fake.word(p_locale, 'state', p_seed, p_position, 'state', v_state);
    CALL fake.uniform_value(p_locale, p_seed, p_position, 'house', v_u);
    v_house := floor(v_u * 999)::integer + 1;
    CALL fake.uniform_value(p_locale, p_seed, p_position, 'postcode', v_u);
    v_postcode := lpad(floor(v_u * 100000)::text, 5, '0');
    CALL fake.uniform_value(p_locale, p_seed, p_position, 'address.format', v_u);
    IF p_locale = 'de_DE' THEN
        v_address := v_street || v_suffix || ' ' || v_house || ', ' || v_postcode || ' ' || v_city;
        IF v_u < 0.3 THEN
            v_address := v_street || v_suffix || ' ' || v_house || E'\n' || v_postcode || ' ' || v_city || ', Deutschland';
        END IF;
    ELSE
        v_address := v_house || ' ' || v_street || ' ' || v_suffix || ', ' || v_city || ', ' || v_state || ' ' || v_postcode;
        IF v_u < 0.3 THEN
            v_address := v_house || ' ' || v_street || ' ' || v_suffix || E'\n' || v_city || ', ' || v_state || ' ' || v_postcode || ', USA';
        END IF;
    END IF;
    CALL fake.uniform_value(p_locale, p_seed, p_position, 'latitude', v_u);
    CALL fake.uniform_value(p_locale, p_seed, p_position, 'longitude', v_v);
    v_lat := asin(2 * v_u - 1) * 180 / pi();
    v_lon := (2 * v_v - 1) * 180;
    CALL fake.normal_value(p_locale, p_seed, p_position, 'height', 172, 10, v_height);
    CALL fake.normal_value(p_locale, p_seed, p_position, 'weight', 75, 12, v_weight);
    CALL fake.word(p_locale, 'eye', p_seed, p_position, 'eye', v_eye);
    CALL fake.uniform_value(p_locale, p_seed, p_position, 'phone.number', v_u);
    v_phone_part := floor(v_u * 10000000)::bigint;
    CALL fake.uniform_value(p_locale, p_seed, p_position, 'phone.format', v_v);
    IF p_locale = 'de_DE' THEN
        v_phone := '+49 30 ' || lpad(v_phone_part::text, 7, '0');
        IF v_v < 0.5 THEN
            v_phone := '(030) ' || lpad(v_phone_part::text, 7, '0');
        END IF;
    ELSE
        v_phone := '+1 (555) ' || substr(lpad(v_phone_part::text, 7, '0'), 1, 3) || '-' || right(lpad(v_phone_part::text, 7, '0'), 4);
        IF v_v < 0.5 THEN
            v_phone := '555.' || substr(lpad(v_phone_part::text, 7, '0'), 1, 3) || '.' || right(lpad(v_phone_part::text, 7, '0'), 4);
        END IF;
    END IF;
    v_email := 'user.' || p_position || '.' || substr(md5(p_locale || '|' || p_seed), 1, 8) || '@example.test';
    p_record := jsonb_build_object(
        'index', p_position, 'locale', p_locale, 'full_name', v_name,
        'address', v_address, 'phone', v_phone, 'email', v_email,
        'latitude', round(v_lat::numeric, 6), 'longitude', round(v_lon::numeric, 6),
        'height_cm', round(v_height::numeric, 2), 'weight_kg', round(v_weight::numeric, 2),
        'eye_color', v_eye
    );
END;
$$;

CREATE OR REPLACE PROCEDURE fake.generate_users(
    IN p_locale TEXT, IN p_seed BIGINT, IN p_batch BIGINT,
    IN p_batch_size INTEGER, INOUT p_result JSONB
)
LANGUAGE plpgsql AS $$
DECLARE
    v_index INTEGER;
    v_position BIGINT;
    v_record JSONB;
BEGIN
    IF p_locale IS NULL OR p_seed IS NULL OR p_batch IS NULL OR p_batch_size IS NULL THEN
        RAISE EXCEPTION 'All generation arguments are required';
    END IF;
    IF p_batch < 0 OR p_batch > 1000000000 OR p_batch_size < 1 OR p_batch_size > 10000 THEN
        RAISE EXCEPTION 'Batch must be 0..1000000000; batch size must be 1..10000';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM fake.word_counts WHERE locale = p_locale) THEN
        RAISE EXCEPTION 'Unsupported locale: %', p_locale;
    END IF;
    p_result := '[]'::jsonb;
    FOR v_index IN 0..p_batch_size - 1 LOOP
        v_position := p_batch * p_batch_size + v_index;
        CALL fake.contact(p_locale, p_seed, v_position, v_record);
        p_result := p_result || jsonb_build_array(v_record);
    END LOOP;
END;
$$;
