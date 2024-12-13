# collection.py
from thinkific import Client

class Collection:
    def __init__(self, client):
        """
        Initialize the Collection class with the client instance.
        """
        self.__client = client

    def list_collections(self, page: int = None, limit: int = None):
        """
        List collections with optional pagination.

        Args:
            page (int): Page number.
            limit (int): Number of results per page.

        Returns:
            dict: Response from the Thinkific API.
        """
        params = {"page": page, "limit": limit}
        return self.__client.request("get", "/collections", params=params)

    def retrieve_collection(self, id: int):
        """
        Retrieve details of a specific collection by ID.

        Args:
            id (int): Collection ID.

        Returns:
            dict: Response from the Thinkific API.
        """
        return self.__client.request("get", f"/collections/{id}")

    def create_collection(self, data: dict):
        """
        Create a new collection.

        Args:
            data (dict): Data to create the collection.

        Returns:
            dict: Response from the Thinkific API.
        """
        return self.__client.request("post", "/collections", json=data)

    def update_collection(self, id: int, data: dict):
        """
        Update an existing collection by ID.

        Args:
            id (int): Collection ID.
            data (dict): Updated data for the collection.

        Returns:
            dict: Response from the Thinkific API.
        """
        return self.__client.request("put", f"/collections/{id}", json=data)

    def delete_collection(self, id: int):
        """
        Delete a specific collection by ID.

        Args:
            id (int): Collection ID.

        Returns:
            dict: Response from the Thinkific API.
        """
        return self.__client.request("delete", f"/collections/{id}")
