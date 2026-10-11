SELECT root,COUNT(*) descendants,SUM(downloads) downloads,1.0*COUNT(*)/SUM(COUNT(*)) OVER() model_share,1.0*SUM(downloads)/NULLIF(SUM(SUM(downloads)) OVER(),0) download_share FROM observations GROUP BY root ORDER BY downloads DESC,root;
SELECT root_resolved,cycle,COUNT(*) models,AVG(depth) mean_depth FROM observations GROUP BY root_resolved,cycle ORDER BY root_resolved,cycle;
