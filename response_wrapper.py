import json


class ResponseWrapper:

    def __init__(self, json: dict):
        self.json = json

    def get(self, path: str) -> dict | str | None:
        """
        Outputs the dict or str corresponding to the provided path.
        Path is of form <data_1>.<data_2> and wil output the json of 
        the provided path
        returns None if nothing was found for the required path
        """
        path_list = path.split(".")
        res = self.json

        for e in path_list:
            if e not in res.keys():
                return None
            res = res[e]

        return res
    

    def get_result_body(self):
        return self.get("result.body")
