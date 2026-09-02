import { BrokerDO } from "./broker";

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

      return await obj.fetch("/_broadcast", {
        method: "POST",
        body: JSON.stringify(payload),
        headers: { "Content-Type": "application/json" },
      });
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
