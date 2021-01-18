import unittest
import weaviate


class TestAuthentication(unittest.TestCase):

    def test_client_credentials(self):
        """
        Test AuthClientCredentials.
        """

        token = "testtoken4711"
        credentials = weaviate.AuthClientCredentials(token)
        request_body = credentials.get_credentials()
        self.assertTrue("grant_type" in request_body)
        self.assertTrue("client_secret" in request_body)

        self.assertEqual(request_body["client_secret"], token)
        self.assertEqual(request_body["grant_type"], "client_credentials")

    def test_user_password(self):
        """
        Test AuthClientPassword.
        """

        user = "@greenstalone"
        password = "testtoken4711"
        credentials = weaviate.AuthClientPassword(user, password)
        request_body = credentials.get_credentials()

        self.assertEqual(request_body["username"], user)
        self.assertEqual(request_body["password"], password)
        self.assertEqual(request_body["grant_type"], "password")
