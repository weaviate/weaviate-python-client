def runREST(RESTurl, weaviateObj, tryTimes, RESTtype):
    if RESTtype == "GET":
        try:
            r = requests.get(url=RESTurl, headers=AUTHENTICATION.defineAuthHeader(), timeout=(2, 20))
        except Exception as e:
            # sleep for 2 sec, wait to come back and run again
            log("WARNING - GET - Some kind of timeout, sleep and wait, try again or fail")
            log("WARNING - REQUEST WAS: " + RESTurl + " " + json.dumps(weaviateObj))
            time.sleep(0.5)
            r = requests.get(url=RESTurl, headers=AUTHENTICATION.defineAuthHeader(), timeout=(2, 20))
    elif RESTtype == "POST":
        try:
            r = requests.post(url=RESTurl + "?rnd=" + str(random.randint(1, 9999999)), data=json.dumps(weaviateObj),
                              headers=AUTHENTICATION.defineAuthHeader(), timeout=(2, 20))
        except Exception as e:
            # sleep for 2 sec, wait to come back and run again
            log("WARNING - POST - Some kind of timeout, sleep and wait, try again or fail")
            log("WARNING _ REQUEST WAS: " + RESTurl + " " + json.dumps(weaviateObj))
            time.sleep(0.5)
            r = requests.post(url=RESTurl, data=json.dumps(weaviateObj), headers=AUTHENTICATION.defineAuthHeader(),
                              timeout=(2, 20))
    elif RESTtype == "PATCH":
        try:
            r = requests.patch(url=RESTurl, data=json.dumps(weaviateObj), headers=AUTHENTICATION.defineAuthHeader(),
                               timeout=(2, 20))
        except Exception as e:
            # sleep for 30 sec, wait to come back and run again
            log("WARNING - PATCH - Some kind of timeout, sleep and wait, try again or fail")
            log("WARNING - REQUEST WAS: " + RESTurl + " " + json.dumps(weaviateObj))
            time.sleep(0.5)
            r = requests.patch(url=RESTurl, data=json.dumps(weaviateObj), headers=AUTHENTICATION.defineAuthHeader(),
                               timeout=(2, 20))
    else:
        log("ERROR: wrong RESTtype is set")
        exit(1)

    if r.status_code != 200:

        try:
            if 'already exists' in r.json()['error'][0]['message']:
                # Client error continue
                return None
        except KeyError:
            pass
        except Exception as e:
            print('Unexepected exception: ' + str(e))

        log("WARNING: STATUS CODE WAS NOT 200 but " + str(r.status_code) + " with: " + str(
            r.json()) + " | RETRY...")

        # weaviate needs some time
        time.sleep(0.5)

        global retriesUntilUltimateFail
        if tryTimes < retriesUntilUltimateFail:
            tryTimes += 1
            return runREST(RESTurl, weaviateObj, tryTimes, RESTtype)
        else:
            log("ERROR: Could not add this thing or action")
            log("ERROR: STATUS CODE WAS NOT 200 but " + str(r.status_code))
            log("ERROR: " + r.text)
            log("ERROR: request URL" + RESTurl)
            log("ERROR: request body: " + json.dumps(weaviateObj))
            return None
    else:
        return r


def getHeadersForRequest(self, shouldAuthenticate):
    """Returns the correct headers for a request"""

    headers = {"content-type": "application/json"}
    # status, _ = self.Get("/.well-known/openid-configuration")

    # Add bearer if OAuth
    # if status == 200:
    if shouldAuthenticate == True:
        headers["Authorization"] = "Bearer " + self.config["auth_bearer"]

    return headers


def AuthGetBearer(self):
    # collect data for the request
    try:
        request = requests.get(self.config['url'] + "/v1/.well-known/openid-configuration",
                               headers={"content-type": "application/json"})
    except urllib.error.HTTPError as error:
        Helpers(None).Error(Messages().Get(210))
    if request.status_code != 200:
        Helpers(None).Error(Messages().Get(210))

    # Set the client ID
    clientId = request.json()['clientId']

    # request additional information
    try:
        requestThirdParth = requests.get(request.json()['href'], headers={"content-type": "application/json"})
    except urllib.error.HTTPError as error:
        Helpers(None).Error(Messages().Get(219))
    if requestThirdParth.status_code != 200:
        Helpers(None).Error(Messages().Get(219))

    # Validate third part auth info
    if 'client_credentials' not in requestThirdParth.json()['grant_types_supported']:
        Helpers(None).Error(Messages().Get(220))

    # Set the body
    requestBody = {
        "client_id": clientId,
        "grant_type": 'client_credentials',
        "client_secret": self.config['auth_clientsecret']
    }

    # try the request
    try:
        request = requests.post(requestThirdParth.json()['token_endpoint'], requestBody)
    except urllib.error.HTTPError as error:
        self.helpers(self.config).Error(Messages().Get(216))

    # sleep to process
    time.sleep(2)

    # Update the config file and self
    accessToken = request.json()['access_token']
    authExpires = int(self.GetEpochTime() + request.json()['expires_in'] - 2)
    Init().UpdateConfigFile('auth_bearer', accessToken)
    Init().UpdateConfigFile('auth_expires', authExpires)
    self.config['auth_bearer'] = accessToken
    self.config['auth_expires'] = authExpires


def Auth(self):
    """Returns true if one should authenticate"""

    # try to make the well known request
    try:
        request = requests.get(self.config["url"] + "/v1/.well-known/openid-configuration",
                               headers=self.getHeadersForRequest(False))
    except urllib.error.HTTPError as error:
        return False

    if request.status_code == 200:
        if (self.config['auth_expires'] - 2) < self.GetEpochTime():  # -2 for some lagtime
            self.helpers(self.config).Info(Messages().Get(141))
            self.auth_get_bearer()

        return True

    return False


def Ping(self):
    """This function pings a Weaviate to see if it is online."""

    self.helpers(self.config).Info("Ping Weaviate...")

    # get the meta endpoint
    try:
        status, _ = self.Get("/schema")
    except:
        self.helpers(self.config).Error(Messages().Get(210))
    # throw error if failed
    if status != 200 or status == None:
        self.helpers(self.config).Error(Messages().Get(210))
    # would fail is not available.
    self.helpers(self.config).Info("Pong from Weaviate...")


def Delete(self, path):
    """This function deletes from a Weaviate."""

    # Authenticate
    shouldAuthenticate = self.Auth()

    # try to request
    try:
        request = requests.delete(self.config["url"] + "/v1" + path,
                                  headers=self.getHeadersForRequest(shouldAuthenticate))
    except urllib.error.HTTPError as error:
        return None

    return request.status_code


def Post(self, path, body):
    """This function posts to a Weaviate."""

    # Authenticate
    shouldAuthenticate = self.Auth()

    # try to request
    try:
        request = requests.post(self.config["url"] + "/v1" + path, json.dumps(body),
                                headers=self.getHeadersForRequest(shouldAuthenticate))
    except urllib.error.HTTPError as error:
        return 0, json.loads(error.read().decode('utf-8'))

    # return the values
    if len(request.json()) == 0:
        return request.status_code, {}
    else:
        return request.status_code, request.json()


def Get(self, path):
    """This function GETS from a Weaviate Weaviate."""

    shouldAuthenticate = self.Auth()

    # try to request
    try:
        request = requests.get(self.config["url"] + "/v1" + path,
                               headers=self.getHeadersForRequest(shouldAuthenticate))
    except urllib.error.HTTPError as error:
        return None, json.loads(error.read().decode('utf-8'))

    return request.status_code, request.json()


# Add a things to Weaviate
def addToWeaviate(localId, className, obj):
    weaviateObj = {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, localId)),
        "class": className,
        "schema": delNone(obj)
    }

    r = runREST(AUTHENTICATION.getWeaviateURL() + "/v1/things", weaviateObj, 0, "POST")

    if r == None:
        return None

    if "id" in r.json():
        resultId = r.json()["id"]
        log("SUCCESS (" + className + "): " + resultId)
        return resultId

    return None