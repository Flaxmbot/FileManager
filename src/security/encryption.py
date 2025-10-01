"""
RSA-4096 encryption manager for secure communication
"""

import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend

from src.config.settings import settings


class EncryptionManager:
    """RSA-4096 encryption manager for secure communication"""

    _instance = None
    _private_key = None
    _public_key = None
    _fernet_key = None
    _aes_key = None
    _aes_iv = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EncryptionManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(cls):
        """Initialize encryption keys"""
        instance = cls()

        # Create keys directory if it doesn't exist
        keys_dir = os.path.dirname(settings.RSA_PRIVATE_KEY_PATH)
        if keys_dir and not os.path.exists(keys_dir):
            os.makedirs(keys_dir, mode=0o700, exist_ok=True)

        # Generate or load RSA keys
        if not os.path.exists(settings.RSA_PRIVATE_KEY_PATH):
            await instance._generate_rsa_keys()

        await instance._load_rsa_keys()

        # Generate symmetric encryption keys
        instance._fernet_key = Fernet.generate_key()
        instance._aes_key = os.urandom(32)  # 256-bit key
        instance._aes_iv = os.urandom(16)   # 128-bit IV

    async def _generate_rsa_keys(self):
        """Generate new RSA-4096 key pair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
        )

        # Save private key
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                settings.SECRET_KEY.encode()
            )
        )

        with open(settings.RSA_PRIVATE_KEY_PATH, 'wb') as f:
            os.chmod(settings.RSA_PRIVATE_KEY_PATH, 0o600)
            f.write(pem)

        # Save public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        with open(settings.RSA_PUBLIC_KEY_PATH, 'wb') as f:
            os.chmod(settings.RSA_PUBLIC_KEY_PATH, 0o644)
            f.write(public_pem)

    async def _load_rsa_keys(self):
        """Load RSA keys from files"""
        # Load private key
        with open(settings.RSA_PRIVATE_KEY_PATH, 'rb') as f:
            self._private_key = serialization.load_pem_private_key(
                f.read(),
                password=settings.SECRET_KEY.encode(),
            )

        # Load public key
        with open(settings.RSA_PUBLIC_KEY_PATH, 'rb') as f:
            self._public_key = serialization.load_pem_public_key(
                f.read(),
            )

    def encrypt_message(self, message: str) -> bytes:
        """Encrypt message using RSA-4096"""
        if not self._public_key:
            raise RuntimeError("Encryption manager not initialized")

        encrypted = self._public_key.encrypt(
            message.encode('utf-8'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return encrypted

    def decrypt_message(self, encrypted_data: bytes) -> str:
        """Decrypt message using RSA-4096"""
        if not self._private_key:
            raise RuntimeError("Encryption manager not initialized")

        decrypted = self._private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted.decode('utf-8')

    def encrypt_file_data(self, data: bytes) -> bytes:
        """Encrypt file data using AES-256"""
        from cryptography.hazmat.primitives.ciphers import Cipher

        if not self._aes_key or not self._aes_iv:
            raise RuntimeError("Encryption manager not initialized")

        cipher = Cipher(algorithms.AES(self._aes_key), modes.CBC(self._aes_iv))
        padder = PKCS7(algorithms.AES.block_size).padder()

        padded_data = padder.update(data) + padder.finalize()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        return encrypted_data

    def decrypt_file_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt file data using AES-256"""
        from cryptography.hazmat.primitives.ciphers import Cipher

        if not self._aes_key or not self._aes_iv:
            raise RuntimeError("Encryption manager not initialized")

        cipher = Cipher(algorithms.AES(self._aes_key), modes.CBC(self._aes_iv))
        unpadder = PKCS7(algorithms.AES.block_size).unpadder()

        decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()
        decrypted_data = unpadder.update(decrypted_padded) + unpadder.finalize()

        return decrypted_data

    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data using Fernet"""
        if not self._fernet_key:
            raise RuntimeError("Encryption manager not initialized")

        fernet = Fernet(self._fernet_key)
        encrypted = fernet.encrypt(data.encode('utf-8'))
        return encrypted.decode('utf-8')

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data using Fernet"""
        if not self._fernet_key:
            raise RuntimeError("Encryption manager not initialized")

        fernet = Fernet(self._fernet_key)
        decrypted = fernet.decrypt(encrypted_data.encode('utf-8'))
        return decrypted.decode('utf-8')

    def get_public_key_pem(self) -> str:
        """Get public key in PEM format"""
        if not self._public_key:
            raise RuntimeError("Encryption manager not initialized")

        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

    def sign_data(self, data: bytes) -> bytes:
        """Sign data using RSA private key"""
        if not self._private_key:
            raise RuntimeError("Encryption manager not initialized")

        signature = self._private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature

    def verify_signature(self, data: bytes, signature: bytes) -> bool:
        """Verify data signature using RSA public key"""
        if not self._public_key:
            raise RuntimeError("Encryption manager not initialized")

        try:
            self._public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False

    def generate_device_token(self) -> str:
        """Generate secure token for device authentication"""
        import secrets
        return secrets.token_urlsafe(32)

    def hash_token(self, token: str) -> str:
        """Hash token for secure storage"""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()