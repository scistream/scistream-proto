
### FAQ

- If the request can't be authenticated make sure that your authentication token is up to date for the correct scope_id.

- Also ensure the request is using the correct scope
```
s2uc logout
s2uc login --scope abcdef
s2uc prod-req --scope abcdef
```

## Scope configuration

To create a scope we must use the globus auth API. Here is an example of how to do so.

curl -s -u "$CLIENT_ID:$CLIENT_SECRET" -H \
    'Content-Type: application/json' \
    -X POST https://auth.globus.org/v2/api/clients/$CLIENT_ID/scopes \
    -d '{
        "scope": {
            "name": "Scistream Operations",
            "description": "All Operations on Scistream",
            "scope_suffix": "scistream",
            "dependent_scopes": [
                    {
                        "optional": false,
                        "requires_refresh_token": true,
                        "scope": "73320ffe-4cb4-4b25-a0a3-83d53d59ce4f"
                    }
                ],
            "advertised": false,
            "allow_refresh_tokens": true
        }
    }' | jq

    ## 5.4? Securing Your Streams [WIP]

    To ensure the security of your data streams, consider the following best practices:

    - Use encrypted communication channels (e.g., SSL/TLS) for all data transfers between the producer, consumer, and SciStream components.
    - Regularly rotate and update access tokens and credentials to minimize the risk of unauthorized access.
    - Implement proper access control mechanisms, granting permissions only to authorized users and applications.
    - Monitor and audit access logs to detect any suspicious activities or unauthorized access attempts.
