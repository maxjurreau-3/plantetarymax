export class BrokerDO {
  state: DurableObjectState;
  env: any;
  clients: Map<string, { controller: ReadableStreamDefaultController<string> }>;
  nextClientId: number;

  constructor(state: DurableObjectState, env: any) {
    this.state = state;
    this.env = env;
    this.clients = new Map();
    this.nextClientId = 1;
  }

  async fetch(request: Request) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (path === "/events/sse") {
      return await this.handleSSE(request, url);
    }

    if (path === "/_broadcast" && request.method === "POST") {
      try {
        const payload = await request.json();
        this._broadcast(payload);
        await this._maybeSaveSnapshot(payload);
        return new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      } catch (err) {
        return new Response("invalid payload", { status: 400 });
      }
    }

    if (path === "/events/snapshot" && request.method === "GET") {
      try {
        const snapshot = await this.state.storage.get("snapshot");
        return new Response(JSON.stringify(snapshot || {}), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      } catch (e) {
        return new Response("{}", {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
    }

    if (path === "/healthz") {
      return new Response(
        JSON.stringify({ ok: true, ts: Date.now() / 1000 }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    return new Response("not found", { status: 404 });
  }

  async handleSSE(request: Request, url: URL) {
    const headers = new Headers({
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    });

    const stream = new ReadableStream<string>({
      start: async (controller) => {
        const clientId = String(this.nextClientId++);
        // @ts-ignore
        this.clients.set(clientId, { controller });

        const init = {
          id: `conn-${Date.now()}`,
          type: "connection.open",
          channel: url.searchParams.get("channel") || "global",
          payload: {},
          ts: Date.now() / 1000,
        };
        controller.enqueue(encodeSSE(init));

        await this._maybeSaveSnapshot(init);

        const keepAlive = setInterval(() => {
          try {
            controller.enqueue(":\n\n");
          } catch (e) {}
        }, 20000);

        const closed = (controller as any).closed as Promise<void>;
        if (closed && typeof closed.then === "function") {
          closed.finally(() => {
            clearInterval(keepAlive);
            this.clients.delete(clientId);
          });
        }
      },
    });

    return new Response(stream, { headers });
  }

  _broadcast(payload: any) {
    const data = JSON.stringify(payload);
    for (const [id, client] of this.clients.entries()) {
      try {
        client.controller.enqueue(encodeRawSSE(data));
      } catch (e) {
        this.clients.delete(id);
      }
    }
  }

  async _maybeSaveSnapshot(envelope: any) {
    try {
      await this.state.storage.put("snapshot", envelope);
    } catch (e) {}
  }
}

function encodeSSE(obj: any) {
  const data = JSON.stringify(obj);
  return `data: ${data}\n\n`;
}

function encodeRawSSE(data: string) {
  return `data: ${data}\n\n`;
}

export default {
  async fetch(request: Request, env: any) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    if (pathname === "/events/publish" && request.method === "POST") {
      const auth =
        request.headers.get("Authorization") ||
        request.headers.get("authorization") ||
        "";
      let token: string | null = null;
      if (auth.toLowerCase().startsWith("bearer "))
        token = auth.split(/\s+/, 2)[1];
      if (!token) token = request.headers.get("x-events-token");
      if (!token || token !== env.EVENTS_PUBLISH_TOKEN) {
        return new Response("unauthorized", { status: 401 });
      }

      let payload: any = null;
      try {
        payload = await request.json();
      } catch (e) {
        return new Response("invalid json", { status: 400 });
      }

      const channel =
        (payload && payload.channel && String(payload.channel)) ||
        url.searchParams.get("channel") ||
        "global";

      const id = env.BROKER_DO.idFromName(channel);
      const obj = env.BROKER_DO.get(id);

      // Use an absolute URL (as a Request) when invoking the Durable Object stub.
      // Some runtimes require absolute URLs rather than path-only strings.
      const broadcastUrl = new URL("/_broadcast", url.origin).toString();
      const broadcastRequest = new Request(broadcastUrl, {
        method: "POST",
        body: JSON.stringify(payload),
        headers: { "Content-Type": "application/json" },
      });
      return await obj.fetch(broadcastRequest);
    }

    if (pathname.startsWith("/events/")) {
      const channel = url.searchParams.get("channel") || "global";
      const id = env.BROKER_DO.idFromName(channel);
      const obj = env.BROKER_DO.get(id);
      return await obj.fetch(request);
    }

    if (pathname === "/healthz") {
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response("not found", { status: 404 });
  },
};
