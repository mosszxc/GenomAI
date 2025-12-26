-- Migration: 016_buyer_multi_geo_vertical
-- Description: Support multiple geos and verticals per buyer
-- Issue: #126

-- Step 1: Add new array columns
ALTER TABLE genomai.buyers
ADD COLUMN IF NOT EXISTS geos text[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS verticals text[] DEFAULT '{}';

-- Step 2: Migrate existing data (single value -> array)
UPDATE genomai.buyers
SET geos = CASE WHEN geo IS NOT NULL THEN ARRAY[geo] ELSE '{}' END,
    verticals = CASE WHEN vertical IS NOT NULL THEN ARRAY[vertical] ELSE '{}' END
WHERE geos = '{}' OR verticals = '{}';

-- Step 3: Create helper function to normalize array of geos
CREATE OR REPLACE FUNCTION genomai.normalize_geos(p_geos text[])
RETURNS text[]
LANGUAGE plpgsql
AS $$
DECLARE
    result text[] := '{}';
    geo_item text;
    normalized text;
BEGIN
    FOREACH geo_item IN ARRAY p_geos
    LOOP
        normalized := genomai.normalize_geo(TRIM(geo_item));
        IF normalized IS NOT NULL AND normalized != '' THEN
            result := array_append(result, normalized);
        END IF;
    END LOOP;
    -- Remove duplicates and sort
    SELECT ARRAY(SELECT DISTINCT unnest(result) ORDER BY 1) INTO result;
    RETURN result;
END;
$$;

-- Step 4: Create helper function to normalize array of verticals
CREATE OR REPLACE FUNCTION genomai.normalize_verticals(p_verticals text[])
RETURNS text[]
LANGUAGE plpgsql
AS $$
DECLARE
    result text[] := '{}';
    vert_item text;
    normalized text;
BEGIN
    FOREACH vert_item IN ARRAY p_verticals
    LOOP
        normalized := genomai.normalize_vertical(TRIM(vert_item));
        IF normalized IS NOT NULL AND normalized != '' THEN
            result := array_append(result, normalized);
        END IF;
    END LOOP;
    -- Remove duplicates and sort
    SELECT ARRAY(SELECT DISTINCT unnest(result) ORDER BY 1) INTO result;
    RETURN result;
END;
$$;

-- Step 5: Create new version of create_buyer_normalized that accepts arrays
CREATE OR REPLACE FUNCTION genomai.create_buyer_normalized(
    p_telegram_id text,
    p_telegram_username text,
    p_name text,
    p_geo text,      -- Can be comma-separated: "DE, MX, US"
    p_vertical text, -- Can be comma-separated: "POT, WL"
    p_keitaro_source text
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    input_geos text[];
    input_verticals text[];
    normalized_geos text[];
    normalized_verticals text[];
    new_buyer genomai.buyers;
BEGIN
    -- Parse comma-separated inputs into arrays
    input_geos := string_to_array(UPPER(REPLACE(p_geo, ' ', '')), ',');
    input_verticals := string_to_array(UPPER(REPLACE(p_vertical, ' ', '')), ',');

    -- Normalize each element
    normalized_geos := genomai.normalize_geos(input_geos);
    normalized_verticals := genomai.normalize_verticals(input_verticals);

    -- Insert buyer with normalized values
    INSERT INTO genomai.buyers (
        telegram_id,
        telegram_username,
        name,
        geo,           -- Keep legacy field (first value)
        vertical,      -- Keep legacy field (first value)
        geos,          -- New array field
        verticals,     -- New array field
        keitaro_source
    ) VALUES (
        p_telegram_id,
        p_telegram_username,
        p_name,
        normalized_geos[1],      -- First geo for backwards compatibility
        normalized_verticals[1], -- First vertical for backwards compatibility
        normalized_geos,
        normalized_verticals,
        LOWER(TRIM(p_keitaro_source))
    )
    RETURNING * INTO new_buyer;

    -- Return buyer data with normalization info
    RETURN jsonb_build_object(
        'id', new_buyer.id,
        'telegram_id', new_buyer.telegram_id,
        'name', new_buyer.name,
        'geo', new_buyer.geo,
        'geos', new_buyer.geos,
        'geo_original', p_geo,
        'vertical', new_buyer.vertical,
        'verticals', new_buyer.verticals,
        'vertical_original', p_vertical,
        'keitaro_source', new_buyer.keitaro_source,
        'created_at', new_buyer.created_at
    );
END;
$$;

-- Step 6: Add comments
COMMENT ON COLUMN genomai.buyers.geos IS 'Array of canonical geo codes (e.g., {MX,DE,US}). Supports multiple geos per buyer.';
COMMENT ON COLUMN genomai.buyers.verticals IS 'Array of canonical vertical codes (e.g., {POT,WL}). Supports multiple verticals per buyer.';
COMMENT ON COLUMN genomai.buyers.geo IS 'DEPRECATED: Primary geo for backwards compatibility. Use geos[] instead.';
COMMENT ON COLUMN genomai.buyers.vertical IS 'DEPRECATED: Primary vertical for backwards compatibility. Use verticals[] instead.';
