import unittest
import os
import sys
import tempfile
import base64
import json
from unittest.mock import patch, MagicMock

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.encryption import generate_user_key, encrypt_data, decrypt_data
import src.config

class TestEncryption(unittest.TestCase):
    """Test cases for encryption and decryption functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create test secret and system salts
        self.test_secret_salt = base64.b64decode("VGVzdFNlY3JldFNhbHQ=")  # "TestSecretSalt" encoded
        self.test_system_salt = base64.b64decode("VGVzdFN5c3RlbVNhbHQ=")  # "TestSystemSalt" encoded
        
        # Mock the config module's salts
        src.config.SECRET_SALT = self.test_secret_salt
        src.config.SYSTEM_SALT = self.test_system_salt

    def test_generate_user_key(self):
        """Test that user keys are generated consistently for the same user but differently for different users."""
        # Generate keys for the same user multiple times
        chat_id = 123456789
        key1 = generate_user_key(chat_id)
        key2 = generate_user_key(chat_id)
        
        # Keys for the same user should be identical
        self.assertEqual(key1, key2)
        
        # Generate key for a different user
        different_chat_id = 987654321
        different_key = generate_user_key(different_chat_id)
        
        # Keys for different users should be different
        self.assertNotEqual(key1, different_key)

    def test_encrypt_decrypt_cycle(self):
        """Test that data can be encrypted and then decrypted back to the original."""
        chat_id = 123456789
        original_data = {
            "date": "2023-01-01",
            "mood": "8",
            "sleep": "7",
            "comment": "Test comment",
            "balance": "6",
            "mania": "3",
            "depression": "2",
            "anxiety": "4",
            "irritability": "3",
            "productivity": "8",
            "sociability": "7"
        }
        
        # Encrypt the data
        encrypted_data = encrypt_data(original_data, chat_id)
        
        # Encrypted data should be a string
        self.assertIsInstance(encrypted_data, str)
        
        # Decrypt the data
        decrypted_data = decrypt_data(encrypted_data, chat_id)
        
        # Decrypted data should match the original
        self.assertEqual(original_data, decrypted_data)

    def test_decrypt_with_wrong_user(self):
        """Test that data encrypted for one user cannot be decrypted by another."""
        chat_id_1 = 123456789
        chat_id_2 = 987654321
        
        test_data = {"date": "2023-01-01", "mood": "8", "comment": "Test"}
        
        # Encrypt for user 1
        encrypted_data = encrypt_data(test_data, chat_id_1)
        
        # Try to decrypt with user 2's key
        decrypted_data = decrypt_data(encrypted_data, chat_id_2)
        
        # Should return None for failed decryption
        self.assertIsNone(decrypted_data)

    def test_different_encryption_for_same_data(self):
        """Test that the same data encrypted twice produces different ciphertexts (due to Fernet's IV)."""
        chat_id = 123456789
        test_data = {"date": "2023-01-01", "mood": "8", "comment": "Test"}
        
        # Encrypt the same data twice
        encrypted_1 = encrypt_data(test_data, chat_id)
        encrypted_2 = encrypt_data(test_data, chat_id)
        
        # Ciphertexts should be different due to random IV
        self.assertNotEqual(encrypted_1, encrypted_2)
        
        # But both should decrypt to the same original data
        decrypted_1 = decrypt_data(encrypted_1, chat_id)
        decrypted_2 = decrypt_data(encrypted_2, chat_id)
        
        self.assertEqual(decrypted_1, test_data)
        self.assertEqual(decrypted_2, test_data)

if __name__ == '__main__':
    unittest.main()