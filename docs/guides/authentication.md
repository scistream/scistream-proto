# Authentication and Security

This guide covers SciStream's control plane authentication framework using Globus Auth, configuration settings, and troubleshooting tips.

## Control Plane Security

SciStream implements security at the control plane level, which manages the setup and teardown of data streaming connections. The actual data transfer occurs through separate channels configured by the control plane.

> **Note:** While you can disable control plane authentication during development and integration testing, it is strongly recommended to enable authentication in production environments.

## Globus Auth Integration

SciStream currently integrates with Globus Auth to provide secure, federated identity management. This enables:

- Authentication using existing institutional credentials
- OAuth 2.0-based access control
- Secure token handling without direct credential sharing

> **Future Plans:** SciStream plans to support additional authentication frameworks to better address multi-institutional authentication scenarios.

For more details, see the [Globus Auth documentation](https://docs.globus.org/api/auth/).

## Prerequisites

- A Globus account ([create one here](https://www.globus.org/signup))
- SciStream installed on your system
- Basic understanding of OAuth 2.0 concepts

## Authentication Configuration

### Obtaining Globus Auth Credentials

1. Log in to the [Globus Developer Portal](https://developers.globus.org/)
2. Create a new project and register a new app
3. Note the Client ID and Client Secret for your app
4. Configure domain restrictions as needed

### Configuring S2CS (SciStream Control Server)

Start S2CS with authentication parameters:

```bash
s2cs -t Haproxy --verbose --client_id="YOUR_CLIENT_ID" --client_secret="YOUR_CLIENT_SECRET"
```

If `client_id` and `client_secret` are omitted, authentication will be disabled, which is acceptable for development but not recommended for production.

### S2UC Authentication Commands

#### Login to obtain access tokens
```bash
s2uc login --scope YOUR_SCOPE_ID
```

#### Verify credentials
```bash
s2uc check-auth --scope YOUR_SCOPE_ID
```

#### Logout and revoke tokens
```bash
s2uc logout
```

#### Include authentication in requests
```bash
s2uc inbound_request --scope YOUR_SCOPE_ID
```

## Authentication Scenarios

### Unauthenticated Server (Development Only)
When S2CS is started without authentication parameters, any client can connect without credentials. This mode is suitable for development and testing but should be avoided in production.

### Authenticated Server (Recommended for Production)
When S2CS is configured with authentication parameters, clients must provide valid credentials:

```bash
# Start server with authentication
s2cs -t Haproxy --verbose --client_id="CLIENT_ID" --client_secret="SECRET"

# Client must login first
s2uc login --scope SCOPE_ID

# Then make authenticated requests
s2uc inbound_request --scope SCOPE_ID
```

### Multiple Authentication Scopes
SciStream supports authentication to multiple scopes:

```bash
# Login to different scopes
s2uc login --scope SCOPE_1
s2uc login --scope SCOPE_2

# Use different scopes for different servers
s2uc inbound_request --s2cs server1:5000 --scope SCOPE_1
s2uc outbound_request --s2cs server2:5000 --scope SCOPE_2 UID PROD_LISTENER
```

## Scope Configuration

To create a custom scope using the Globus Auth API:

```bash
curl -s -u "$CLIENT_ID:$CLIENT_SECRET" -H 'Content-Type: application/json' \
  -X POST https://auth.globus.org/v2/api/clients/$CLIENT_ID/scopes \
  -d '{
      "scope": {
          "name": "SciStream Operations",
          "description": "All Operations on SciStream",
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
  }'
```

## Troubleshooting

### Invalid Token Errors
If you receive "Authentication token is invalid":
1. Verify you've logged in to the correct scope
2. Check if the token has expired and login again
3. Ensure S2CS is configured with the matching client ID

### Common Command Errors
- If `s2uc inbound_request` fails, ensure you're using the correct scope ID
- For "Please obtain new credentials" errors, run `s2uc login --scope SCOPE_ID`