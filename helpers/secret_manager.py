class SecretManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.access_key = ""
        return cls._instance
    
    def __init__(self):
        pass

secret_manager = SecretManager()