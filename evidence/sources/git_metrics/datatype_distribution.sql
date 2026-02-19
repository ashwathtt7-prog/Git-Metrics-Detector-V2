SELECT
    COALESCE(data_type, 'unknown') as data_type,
    COUNT(*) as count
FROM metrics
GROUP BY data_type
ORDER BY count DESC
