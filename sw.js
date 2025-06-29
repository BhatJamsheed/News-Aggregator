self.addEventListener('push', function(event) {
  let data = {};
  try { data = event.data.json(); } catch (e) {}
  self.registration.showNotification(data.title || 'News', {
    body: data.body || '',
    icon: '/static/download.jpeg',
    data: { url: data.url || '/' }
  });
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  if (event.notification.data && event.notification.data.url) {
    event.waitUntil(clients.openWindow(event.notification.data.url));
  }
});

self.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'SHOW_NOTIFICATION') {
    self.registration.showNotification(event.data.title, {
      body: event.data.body,
      icon: '/static/download.jpeg',
      data: { url: event.data.url }
    });
  }
}); 