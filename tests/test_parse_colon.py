import re

def _find_role_by_id_texte_mock(id_texte):
    """
    Mock of the function in webhook_routes.py
    """
    # Format attendu : "NomSanitisé:RoleID:EventID:AppRoot"
    parts = id_texte.split(':')
    if len(parts) >= 2:
        try:
            role_id = int(parts[1])
            return f"Found Role ID: {role_id}"
        except (ValueError, IndexError):
            pass
    return "Not Found"

# Test cases
test_cases = [
    ("PauleGilbert:402:13:gnole_dev", "Found Role ID: 402"),
    ("ClausShnabel:401:14:gnoletest", "Found Role ID: 401"),
    ("SimpleName:123:456", "Found Role ID: 123"),
    ("Malformed:abc:678", "Not Found"),
    ("Old_Format_Underscore_402_13", "Not Found"),
    ("NameOnly", "Not Found")
]

for id_texte, expected in test_cases:
    result = _find_role_by_id_texte_mock(id_texte)
    print(f"Testing '{id_texte}': Expected '{expected}', Got '{result}'")
    assert result == expected

print("\n✅ All tests passed!")
