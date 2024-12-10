# instructor.py
from thinkific import Client
class Instructor:
    def __init__(self, client):
        """
        Initialize the Instructor class with the client instance.
        """
        self.__client = client

    def list_instructors(self, page: int = None, limit: int = None):
        """
        List instructors with optional pagination.

        Args:
            page (int): Page number.
            limit (int): Number of results per page.

        Returns:
            dict: Response from the Thinkific API.
        """
        params = {"page": page, "limit": limit}
        return self.__client.request("get", "/instructors", params=params)

    def retrieve_instructor(self, id: int):
        """
        Retrieve details of a specific instructor by ID.

        Args:
            id (int): Instructor ID.

        Returns:
            dict: Response from the Thinkific API.
        """
        return self.__client.request("get", f"/instructors/{id}")
