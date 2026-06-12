const UA =
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36";

const PRESETS = {
    mp: {
        Referer: "https://mp.weixin.qq.com",
    },
};


function error(code, status = 400, retry = false) {
    const body = JSON.stringify({ error: code, retry });
    return new Response(body, {
        status: status,
        headers: { "Content-Type": "application/json" },
    });
}


/**
 * 解析请求
 */
async function parseRequest(req) {
    const origin = req.headers.get("origin") || '*';

    // 代理目标的请求参数
    let targetURL = '';
    let targetMethod = "GET";
    let targetBody = '';
    let targetHeaders = {};
    let preset = '';

    const method = req.method.toLowerCase();
    if (method === "get") {
        // GET
        // ?url=${encodeURIComponent(https://example.com?a=b)}&method=GET&headers=${encodeURIComponent(JSON.stringify(headers))}
        const {searchParams} = new URL(req.url);
        if (searchParams.has("url")) {
            targetURL = decodeURIComponent(searchParams.get("url"));
        }
        if (searchParams.has("method")) {
            targetMethod = searchParams.get("method");
        }
        if (searchParams.has("body")) {
            targetBody = decodeURIComponent(searchParams.get("body"));
        }
        if (searchParams.has("headers")) {
            try {
                targetHeaders = JSON.parse(
                    decodeURIComponent(searchParams.get("headers")),
                );
            } catch (_) {
                throw { code: "invalid_headers", status: 400, retry: false };
            }
        }
        if (searchParams.has("preset")) {
            preset = decodeURIComponent(searchParams.get("preset"));
        }
    } else if (method === "post") {
        // POST
        /**
         * payload(json):
         * {
         *   url: 'https://example.com',
         *   method: 'PUT',
         *   body: 'a=1&b=2',
         *   headers: {
         *     Cookie: 'name=root'
         *   },
         *   preset: '',
         * }
         */
        const payload = await req.json();
        if (payload.url) {
            targetURL = payload.url;
        }
        if (payload.method) {
            targetMethod = payload.method;
        }
        if (payload.body) {
            targetBody = payload.body;
        }
        if (payload.headers) {
            targetHeaders = payload.headers;
        }
        if (payload.preset) {
            preset = payload.preset;
        }
    } else {
        throw { code: "method_not_allowed", status: 405, retry: false };
    }

    if (!targetURL) {
        throw { code: "no_url", status: 400, retry: false };
    }
    if (!/^https?:\/\//.test(targetURL)) {
        throw { code: "invalid_url", status: 400, retry: false };
    }
    if (targetMethod === "GET" && targetBody) {
        throw { code: "get_body_not_allowed", status: 400, retry: false };
    }
    if (Object.prototype.toString.call(targetHeaders) !== "[object Object]") {
        throw { code: "invalid_headers", status: 400, retry: false };
    }
    if (!targetHeaders["User-Agent"]) {
        targetHeaders["User-Agent"] = UA;
    }

    // 增加预设
    if (preset in PRESETS) {
        Object.assign(targetHeaders, PRESETS[preset]);
    }

    return {
        origin,
        targetURL,
        targetMethod,
        targetBody,
        targetHeaders,
    };
}

const FETCH_TIMEOUT_MS = 12000;

/**
 * 带超时的代理请求
 */
async function proxyFetch(url, method, body, headers = {}) {
    return fetch(url, {
        method: method,
        body: body || undefined,
        headers: new Headers(headers),
        signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
    });
}

export default {
    async fetch(request) {
        const t0 = Date.now();
        const traceId = crypto.randomUUID().substring(0, 8);

        const reqUrl = new URL(request.url);

        if (reqUrl.pathname === "/health") {
            return new Response(JSON.stringify({status: "ok"}), {
                status: 200,
                headers: {"Content-Type": "application/json"},
            });
        }

        if (request.method.toUpperCase() === "OPTIONS") {
            return new Response(null, {
                status: 204,
                headers: {
                    "Access-Control-Allow-Origin": request.headers.get("origin") || "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Max-Age": "86400",
                },
            });
        }

        try {
            const {
                origin,
                targetURL,
                targetMethod,
                targetBody,
                targetHeaders,
            } = await parseRequest(request);

            // 代理请求
            let response;
            try {
                response = await proxyFetch(
                    targetURL,
                    targetMethod,
                    targetBody,
                    targetHeaders,
                );
            } catch (e) {
                if (e.name === "TimeoutError" || e.name === "AbortError") {
                    throw { code: "upstream_timeout", status: 504, retry: true, target: targetURL };
                }
                throw { code: "upstream_unreachable", status: 502, retry: true, target: targetURL };
            }

            console.log(JSON.stringify({
                event: "proxy_ok",
                trace: traceId,
                status: response.status,
                latency_ms: Date.now() - t0,
                target: targetURL.substring(0, 80),
            }));

            const respHeaders = new Headers(response.headers);
            respHeaders.set("Access-Control-Allow-Origin", origin || "*");
            respHeaders.set("Access-Control-Max-Age", "86400");
            respHeaders.set("X-Trace-Id", traceId);

            return new Response(response.body, {
                status: response.status,
                statusText: response.statusText,
                headers: respHeaders,
            });
        } catch (err) {
            console.log(JSON.stringify({
                event: "proxy_fail",
                trace: traceId,
                error: err.code || "internal_error",
                latency_ms: Date.now() - t0,
                target: (err.target || targetURL || reqUrl.href).substring(0, 80),
            }));

            if (err.code) {
                return error(err.code, err.status || 400, err.retry !== false);
            }
            return error("internal_error", 500, false);
        }
    }
};
