# Network and Filesize Limitations

This document outlines the network-related limitations when using Brandy Box over the internet via Cloudflare or CloudFront.

## Cloudflare Limitations

When Brandy Box is proxied through Cloudflare (e.g., using a Cloudflare Tunnel), the following limits apply based on the plan:

| Plan | Client Request Body Limit (Upload Size) |
| :--- | :--- |
| **Free / Pro** | 100 MB |
| **Business** | 200 MB |
| **Enterprise** | 500 MB+ (Configurable) |

### Timeouts
- Cloudflare typically enforces a **100-second** timeout for HTTP responses. If an upload or download takes longer than this without sending any data, the connection may be dropped. Brandy Box's streaming and retry logic helps mitigate this.

---

## AWS CloudFront Limitations

If Brandy Box is deployed behind AWS CloudFront:

### Filesize Limits
- **Maximum Request Body Size**: 64 GB.
- **WAF Inspection**: If AWS WAF is enabled, it only inspects the first **16 KB** to **64 KB** of the body. Large uploads are allowed but only the beginning is inspected for threats.

### Timeouts
- **Origin Response Timeout**: Default is **30 seconds**. This can be increased up to **60 seconds** via the console and up to **600 seconds (10 minutes)** via a service quota increase request.
- **Origin Keep-alive Timeout**: Default is **5 seconds**.

---

## Recommendations for Large Files

1. **Use LAN**: When connected to the local network (`brandstaetter`), the client automatically switches to the local IP (`192.168.0.150`), bypassing these limits.
2. **Chunked Uploads**: (Future improvement) Implementing chunked uploads would allow bypassing the 100MB Cloudflare limit on Free plans.
3. **Unproxied Subdomain**: For very large files over the internet, using an unproxied DNS record (grey-clouded in Cloudflare) or a direct VPN connection to the Raspberry Pi is recommended.
