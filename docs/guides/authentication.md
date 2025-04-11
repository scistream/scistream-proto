# 5. Authentication and Security

This guide covers SciStream's control plane authentication framework using Globus Auth, configuration settings, and troubleshooting tips.

## 5.1 Control Plane Security

SciStream implements security at the control plane level, which manages the setup and teardown of data streaming connections. The actual data transfer occurs through separate channels configured by the control plane.

> **Note:** While you can disable control plane authentication during development and integration testing, it is strongly recommended to enable authentication in production environments.

## 5.2 Globus Auth Integration

SciStream currently integrates with Globus Auth to provide secure, federated identity management. This enables:

- Authentication using existing institutional credentials
- OAuth 2.0-based access control
- Secure token handling without direct credential sharing

> **Future Plans:** SciStream plans to support additional authentication frameworks to better address multi-institutional authentication scenarios.

For more details, see the [Globus Auth documentation](https://docs.globus.org/api/auth/).

## 5.3 Prerequisites

- A Globus account ([create one here](https://www.globus.org/signup))
- SciStream installed on your system
- Basic understanding of OAuth 2.0 concepts

## 5.4 Authentication Configuration

### 5.4.1 Obtaining Globus Auth Credentials

1. Log in to the [Globus Developer Portal](https://developers.globus.org/)
2. Create a new project and register a new app
3. Note the Client ID and Client Secret for your app
4. Configure domain restrictions as needed

### 5.4.2 Configuring S2CS (SciStream Control Server)

Start S2CS with authentication parameters:

```bash
s2cs -t Haproxy --verbose --client_id="YOUR_CLIENT_ID" --client_secret="YOUR_CLIENT_SECRET"
```

If `client_id` and `client_secret` are omitted, authentication will be disabled, which is acceptable for development but not recommended for production.

### 5.4.3 S2UC Authentication Commands

#### 5.4.3.1 Login to obtain access tokens
```bash
s2uc login --scope YOUR_SCOPE_ID
```

#### 5.4.3.2 Verify credentials
```bash
s2uc check-auth --scope YOUR_SCOPE_ID
```

#### 5.4.3.3 Logout and revoke tokens
```bash
s2uc logout
```

#### 5.4.3.4 Include authentication in requests
```bash
s2uc inbound_request --scope YOUR_SCOPE_ID
```

## 5.5 Authentication Scenarios

### 5.5.1 Unauthenticated Server (Development Only)
When S2CS is started without authentication parameters, any client can connect without credentials. This mode is suitable for development and testing but should be avoided in production.

### 5.5.2 Authenticated Server (Recommended for Production)
When S2CS is configured with authentication parameters, clients must provide valid credentials:

```bash
# Start server with authentication
s2cs -t Haproxy --verbose --client_id="CLIENT_ID" --client_secret="SECRET"

# Client must login first
s2uc login --scope SCOPE_ID

# Then make authenticated requests
s2uc inbound_request --scope SCOPE_ID
```

### 5.5.3 Multiple Authentication Scopes
SciStream supports authentication to multiple scopes:

```bash
# Login to different scopes
s2uc login --scope SCOPE_1
s2uc login --scope SCOPE_2

# Use different scopes for different servers
s2uc inbound_request --s2cs server1:5000 --scope SCOPE_1
s2uc outbound_request --s2cs server2:5000 --scope SCOPE_2 UID PROD_LISTENER
```

## 5.6 Scope Configuration

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

## 5.7 Troubleshooting

### 5.7.1 Invalid Token Errors
If you receive "Authentication token is invalid":
1. Verify you've logged in to the correct scope
2. Check if the token has expired and login again
3. Ensure S2CS is configured with the matching client ID

### 5.7.2 Common Command Errors
- If `s2uc inbound_request` fails, ensure you're using the correct scope ID
- For "Please obtain new credentials" errors, run `s2uc login --scope SCOPE_ID`