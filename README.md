# xiaomi mitmproxy

A mitmproxy addon and mitmweb UI patch for inspecting encrypted Xiaomi Cloud API
traffic.

It keeps the original intercepted request and response bodies unchanged, then
adds two detail tabs for matching Xiaomi API flows:

- `Xiaomi Request`
- `Xiaomi Response`

The tabs display decrypted JSON using a collapsible, syntax-colored JSON text
viewer. If decryption fails, the tabs remain available and show the error plus
the original body.

## Features

- Only processes `api.io.mi.com` and its subdomains.
- Extracts `_nonce` and `data` from
  `application/x-www-form-urlencoded` request bodies.
- Decrypts Xiaomi RC4 request and response payloads.
- Preserves the original mitmweb `Request` and `Response` tabs.
- Adds collapsible JSON text views with selectable text for partial copying.
- Keeps Xiaomi tabs visible when decoding fails and displays the raw body.
- Sets the default Flow List search filter to `mi.com`.
- Adds a red `Clear All` button after the top-level tabs without a confirmation
  dialog.

## Requirements

- Python 3.11 or newer
- A phone and the computer running mitmweb on the same local network
- Your Xiaomi Cloud session `ssecurity` value

The UI patch is pinned to:

```text
mitmproxy==12.2.3
```

## Installation

```bash
git clone <your-github-repository-url>
cd xiaomi-mitmproxy

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 patch_mitmweb_comment_preview.py
```

The patch modifies the mitmweb files inside the local `.venv`. Run the patch
script again after recreating the virtual environment or reinstalling
mitmproxy.

## Configure ssecurity

Export the Xiaomi Cloud session key before starting mitmweb:

```bash
export XIAOMI_SSECURITY='your-ssecurity-value'
```

Do not commit a real `ssecurity` value. It is session-specific sensitive data
and may expire when the Xiaomi login session changes.

## Start mitmweb

```bash
source .venv/bin/activate
export XIAOMI_SSECURITY='your-ssecurity-value'
mitmweb -s app.py --listen-host 0.0.0.0 --listen-port 8080
```

Open the web interface on the computer:

```text
http://127.0.0.1:8081
```

After updating the UI patch, force-refresh the browser:

```text
macOS: Cmd + Shift + R
Windows/Linux: Ctrl + Shift + R
```

## Configure a phone proxy

1. Connect the phone and computer to the same Wi-Fi network.
2. Find the computer's local IP address. On macOS:

   ```bash
   ipconfig getifaddr en0
   ```

3. In the phone's Wi-Fi settings, configure the HTTP proxy manually:

   ```text
   Server: <computer-local-ip>
   Port:   8080
   ```

4. On the phone, open:

   ```text
   http://mitm.it
   ```

5. Install the mitmproxy CA certificate for the phone platform.

### iPhone and iPad

After installing the profile, also enable trust:

```text
Settings > General > About > Certificate Trust Settings
```

Enable full trust for the mitmproxy root certificate.

### Android

Install the downloaded certificate as a CA certificate. Android 7 and newer
applications may reject user-installed CAs unless the application explicitly
allows them.

## Usage

1. Start mitmweb and configure the phone proxy.
2. Use the Xiaomi application on the phone.
3. Select a matching flow in the mitmweb Flow List.
4. Open `Xiaomi Request` or `Xiaomi Response`.
5. Click JSON disclosure arrows to collapse or expand nested objects and arrays.
6. Select any visible text fragment to copy part of the JSON.

The standard mitmweb `Request` and `Response` tabs still show the original
encrypted traffic.

## Decode failures

For matching Xiaomi domains, both Xiaomi tabs are always present. A failed
decode displays:

```text
<error message>

Raw body
<original request or response body>
```

Common causes:

- `XIAOMI_SSECURITY` is missing or expired.
- The request does not contain `_nonce` and `data`.
- The endpoint uses a different payload format.
- The response arrived before a usable request nonce was available.

## Tests

```bash
source .venv/bin/activate
python3 -m unittest -v
```

## Limitations

- The mitmweb patch targets `mitmproxy==12.2.3`. A different mitmproxy release
  may require updating `patch_mitmweb_comment_preview.py`.
- The addon only attempts Xiaomi RC4 decoding for `api.io.mi.com` and its
  subdomains.
- Certificate pinning, custom TLS stacks, and applications that bypass the
  system proxy may prevent traffic capture.

## Responsible use

Use this project only with devices, accounts, and traffic you are authorized to
inspect. Decrypted API payloads and Xiaomi session values may contain sensitive
information. Remove the phone proxy and mitmproxy CA certificate when testing
is complete.
