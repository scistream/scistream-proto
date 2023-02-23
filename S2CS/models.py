
from typing import Dict, List

#from typing_extensions import TypedDict

class S2CSException(Exception):
    ##
    pass

class InvalidRequest(S2CSException):
    ##
    pass

def validate_input(model, input):
        model = model.__annotations__
        same_keys = set(model.keys()) == set(data.keys())
        if not same_keys:
            print(
                "model_keys: {}\ndata_keys: {}".format(
                    sorted(model.keys()), sorted(data.keys())
                )
            )
        correct_class = True
        for key, instance_class in model.items():
            same_class = isinstance(data[key], instance_class)
            correct_class = correct_class and same_class
            if not same_class:
                print(
                    "key: {}\nmodel_class: {}\ndata_class: {}".format(
                        key, instance_class, data[key].__class__
                    )
                )
        return correct_class and same_keys

def validate_request(input):
    validate_uid(input)
    if "num_conn" not in input or input["num_conn"] < 0:
        raise InvalidRequest("must have at least one connection")

def validate_uid(input):
    if "uid" not in input or not input["uid"]:
        raise S2CSException("Empty uid")

def validate_update(request, entry):
    if ("s2ds_proc" not in entry) or len(entry["s2ds_proc"]) != entry["num_conn"]:
        raise S2CSException("S2DS subprocess(es) not launched correctly!")
    if request["local_listeners"] != entry["listeners"]:
        raise S2CSException("S2UC connection map does not match S2CS listeners")
    if (entry["role"] == "PROD"):
        if ("prod_listeners" not in entry) or not entry["prod_listeners"]:
            raise S2CSException("Prod S2CS never received or did not correctly process ProdApp Hello")
        if request["remote_listeners"] != entry["prod_listeners"]:
            raise S2CSException("S2UC connection map does not match Prod S2CS ProdApp listeners")
        if len(request["remote_listeners"]) > entry["num_conn"]:
            raise S2CSException("ProdApp cannot have more listeners than Prod S2CS")
    else:
        if len(request["remote_listeners"]) != entry["num_conn"]:
            raise S2CSException("Prod/Cons S2CS must have same number of listeners")
"""
ClientRequest = TypedDict(
    "ClientRequest",
    {
        "uid": str
    },
)

Entry = TypedDict(
    "ClientRequest",
    {
        "uid": str
    },
)
"""
