from lineage.analyse import classify_licence_pair

def test_equal_rank_licenses_do_not_trigger_unknown_root_rule():
 category,note=classify_licence_pair('cc-by-nc-sa-4.0','cc-by-nc-4.0')
 assert category!='widens'
