SELECT
    COALESCE(category, 'uncategorized') as category,
    COUNT(*) as count
FROM metrics
GROUP BY category
ORDER BY count DESC
