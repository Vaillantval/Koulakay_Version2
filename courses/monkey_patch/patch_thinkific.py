# patch_thinkific.py

from thinkific.client import Client
from .instructor import Instructor
from .collection import Collection
from thinkific import Thinkific 

class ThinkificExtend(Thinkific):
    def __init__(self, api_key, subdomain):
        """
        Extend the Thinkific class to include the Instructor module.
        """
        super().__init__(api_key, subdomain)  # Call the parent constructor
        
        client = Client(api_key,subdomain)
        
        self.__instructors = Instructor(client)  # Use the private client from the parent class
        self.__collections = Collection(client)

    @property
    def instructors(self):
        """
        Expose the Instructor module.
        """
        return self.__instructors
    
    @property
    def collections(self):
        """
        Expose the Collections module.
        """
        return self.__collections
