// While Qt sets up the page, `qt` can be missing and the first init message can go unanswered. Wait for an answer
// before asking again: a new QWebChannel takes over the transport, so asking too often loses every reply.
(function connect(attempt) {
  if (window.elucidaHost || attempt > 40) return;
  if (typeof qt === "undefined" || typeof QWebChannel === "undefined") return void setTimeout(() => connect(attempt + 1), 100);
  new QWebChannel(qt.webChannelTransport, channel => { window.elucidaHost = channel.objects.elucidaHost; });
  setTimeout(() => connect(attempt + 1), 3000);
})(0);
