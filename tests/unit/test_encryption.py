import unittest
import os
import sys
import tempfile
import base64
import json
from unittest.mock import patch, MagicMock

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.encryption import (
    generate_user_key, encrypt_data, decrypt_data,
    encrypt_for_sharing, decrypt_shared_data
)
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


class TestSharingEncryption(unittest.TestCase):
    """Test cases for sharing encryption functionality (encrypt_for_sharing/decrypt_shared_data)."""

    def setUp(self):
        """Set up test environment."""
        # Create test system salt
        self.test_system_salt = base64.b64decode("VGVzdFN5c3RlbVNhbHQ=")  # "TestSystemSalt" encoded

        # Mock the config module's system salt
        src.config.SYSTEM_SALT = self.test_system_salt

    def test_encrypt_decrypt_sharing_cycle(self):
        """Test that data can be encrypted for sharing and decrypted with the correct password."""
        password = "test_password_123"
        original_data = [
            {
                "date": "2023-01-01",
                "mood": "8",
                "sleep": "7",
                "comment": "First entry",
                "balance": "6",
                "mania": "3",
                "depression": "2",
                "anxiety": "4",
                "irritability": "3",
                "productivity": "8",
                "sociability": "7"
            },
            {
                "date": "2023-01-02",
                "mood": "7",
                "sleep": "8",
                "comment": "Second entry",
                "balance": "7",
                "mania": "2",
                "depression": "3",
                "anxiety": "3",
                "irritability": "2",
                "productivity": "9",
                "sociability": "8"
            }
        ]

        # Encrypt the data
        encrypted_data = encrypt_for_sharing(original_data, password)

        # Encrypted data should be a string
        self.assertIsInstance(encrypted_data, str)
        self.assertGreater(len(encrypted_data), 0)

        # Decrypt the data with correct password
        decrypted_data = decrypt_shared_data(encrypted_data, password)

        # Decrypted data should match the original
        self.assertIsNotNone(decrypted_data)
        self.assertEqual(original_data, decrypted_data)

    def test_decrypt_shared_with_wrong_password(self):
        """Test that decryption fails with an incorrect password."""
        correct_password = "correct_password"
        wrong_password = "wrong_password"

        test_data = [
            {"date": "2023-01-01", "mood": "8", "comment": "Test entry"}
        ]

        # Encrypt with correct password
        encrypted_data = encrypt_for_sharing(test_data, correct_password)

        # Try to decrypt with wrong password
        decrypted_data = decrypt_shared_data(encrypted_data, wrong_password)

        # Should return None for failed decryption
        self.assertIsNone(decrypted_data)

    def test_decrypt_corrupted_data(self):
        """Test that decryption handles corrupted data gracefully."""
        password = "test_password"

        # Various forms of corrupted data
        corrupted_data_cases = [
            "corrupted_base64_data",  # Invalid base64
            "YWJjZGVmZ2g=",  # Valid base64 but invalid Fernet token
            "",  # Empty string
            "!@#$%^&*()",  # Special characters
        ]

        for corrupted_data in corrupted_data_cases:
            with self.subTest(corrupted_data=corrupted_data):
                decrypted_data = decrypt_shared_data(corrupted_data, password)

                # Should return None for corrupted data
                self.assertIsNone(decrypted_data)

    def test_sharing_with_special_characters_in_password(self):
        """Test encryption/decryption with passwords containing special characters."""
        test_data = [{"date": "2023-01-01", "mood": "8"}]

        special_passwords = [
            "пароль_на_русском",  # Cyrillic characters
            "密碼123",  # Chinese characters
            "p@$$w0rd!#%",  # Special ASCII characters
            "emoji_🔐_password",  # Emoji
            "spaces in password",  # Spaces
        ]

        for password in special_passwords:
            with self.subTest(password=password):
                # Encrypt
                encrypted_data = encrypt_for_sharing(test_data, password)
                self.assertIsInstance(encrypted_data, str)

                # Decrypt with same password
                decrypted_data = decrypt_shared_data(encrypted_data, password)
                self.assertIsNotNone(decrypted_data)
                self.assertEqual(test_data, decrypted_data)

    def test_sharing_empty_data(self):
        """Test encryption of empty data list."""
        password = "test_password"
        empty_data = []

        # Encrypt empty list
        encrypted_data = encrypt_for_sharing(empty_data, password)
        self.assertIsInstance(encrypted_data, str)

        # Decrypt should return empty list
        decrypted_data = decrypt_shared_data(encrypted_data, password)
        self.assertIsNotNone(decrypted_data)
        self.assertEqual(empty_data, decrypted_data)

    def test_sharing_large_dataset(self):
        """Test encryption/decryption of a large dataset (100 entries)."""
        password = "test_password"

        # Create a large dataset
        large_data = []
        for i in range(100):
            large_data.append({
                "date": f"2023-01-{i+1:02d}" if i < 31 else f"2023-02-{i-30:02d}",
                "mood": str((i % 10) + 1),
                "sleep": str((i % 10) + 1),
                "comment": f"Entry number {i+1} with some text",
                "balance": str((i % 10) + 1),
                "mania": str((i % 10) + 1),
                "depression": str((i % 10) + 1),
                "anxiety": str((i % 10) + 1),
                "irritability": str((i % 10) + 1),
                "productivity": str((i % 10) + 1),
                "sociability": str((i % 10) + 1)
            })

        # Encrypt
        encrypted_data = encrypt_for_sharing(large_data, password)
        self.assertIsInstance(encrypted_data, str)

        # Decrypt
        decrypted_data = decrypt_shared_data(encrypted_data, password)
        self.assertIsNotNone(decrypted_data)
        self.assertEqual(len(large_data), len(decrypted_data))
        self.assertEqual(large_data, decrypted_data)

    def test_different_encryption_same_password(self):
        """Test that encrypting the same data with the same password produces different ciphertexts."""
        password = "test_password"
        test_data = [{"date": "2023-01-01", "mood": "8"}]

        # Encrypt the same data twice
        encrypted_1 = encrypt_for_sharing(test_data, password)
        encrypted_2 = encrypt_for_sharing(test_data, password)

        # Ciphertexts should be different due to random IV
        self.assertNotEqual(encrypted_1, encrypted_2)

        # But both should decrypt to the same original data
        decrypted_1 = decrypt_shared_data(encrypted_1, password)
        decrypted_2 = decrypt_shared_data(encrypted_2, password)

        self.assertEqual(decrypted_1, test_data)
        self.assertEqual(decrypted_2, test_data)

    def test_password_case_sensitivity(self):
        """Test that passwords are case-sensitive."""
        test_data = [{"date": "2023-01-01", "mood": "8"}]
        password_lower = "password"
        password_upper = "PASSWORD"

        # Encrypt with lowercase password
        encrypted_data = encrypt_for_sharing(test_data, password_lower)

        # Try to decrypt with uppercase password (should fail)
        decrypted_data = decrypt_shared_data(encrypted_data, password_upper)
        self.assertIsNone(decrypted_data)

        # Decrypt with correct lowercase password (should succeed)
        decrypted_data = decrypt_shared_data(encrypted_data, password_lower)
        self.assertIsNotNone(decrypted_data)
        self.assertEqual(test_data, decrypted_data)


if __name__ == '__main__':
    unittest.main()