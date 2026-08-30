/* 해외 시장 브리핑 서비스워커.
 *
 * 전략: network-first, cache-fallback.
 * 브리핑은 매일 바뀌므로 항상 네트워크를 먼저 시도하고,
 * 지하철 등 오프라인에서는 마지막으로 본 리포트를 보여준다.
 */
const CACHE = "brief-v1";

self.addEventListener("install", (e) => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;

  // 외부 도메인(폰트 CDN, 뉴스 링크)은 건드리지 않는다
  if (new URL(req.url).origin !== self.location.origin) return;

  e.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() =>
        caches.match(req).then(
          (hit) => hit || caches.match("./index.html")
        )
      )
  );
});
