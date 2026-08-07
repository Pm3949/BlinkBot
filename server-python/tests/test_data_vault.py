import sys
import os

# Add server-python to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_vault import secure_pack, secure_unpack

def test_data_vault_pipeline():
    test_strings = [
        "Hello World!",
        "",
        "A" * 1000,
        "Special characters: !@#$%^&*()_+{}|:\"<>?`-=[]\\;',./",
        "Multibyte characters: こんにちは, 안녕하세요, 🧑‍💻"
    ]
    
    for original in test_strings:
        packed = secure_pack(original)
        assert packed != original or original == "", "Packed data should be encrypted base64"
        unpacked = secure_unpack(packed)
        assert unpacked == original, f"Unpacked data '{unpacked}' does not match original '{original}'"

def test_data_vault_fallback():
    # Legacy unencrypted records should be returned exactly as is
    legacy_strings = [
        "Normal unencrypted text",
        "{}",
        "[]"
    ]
    for legacy in legacy_strings:
        assert secure_unpack(legacy) == legacy, "Fallback should return unencrypted strings as-is"

if __name__ == "__main__":
    print("Running data vault test suite...")
    test_data_vault_pipeline()
    test_data_vault_fallback()
    print("All data vault tests passed successfully!")
