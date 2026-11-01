#include "presonus/MeterManagerBase.hpp"
#include <cstring>

namespace Presonus {
void MeterManagerBase::sourcePortStart() { Core::Threads::Thread::start(); }
bool MeterManagerBase::sourcePortJoin(unsigned int milliseconds) {
  return Core::Threads::Thread::join(milliseconds);
}
void MeterManagerBase::sourcePortTerminate() {
  Core::Threads::Thread::terminate();
}
void MeterManagerBase::sourcePortSleep(unsigned int milliseconds) {
  Core::Threads::CurrentThread::sleep(milliseconds);
}
void MeterManagerBase::startup() { sourcePortStart(); }
void MeterManagerBase::shutdown() {
  sourcePortStop = true;
  if (!sourcePortJoin(1000))
    sourcePortTerminate();
}
int MeterManagerBase::threadEntry() {
  const auto previous = sourcePortRunning.exchange(1);
  struct Restore {
    std::atomic<unsigned char> &state;
    unsigned char previous;
    ~Restore() { state = previous; }
  } restore{sourcePortRunning, previous};
  bool phase = false;
  while (!sourcePortStop) {
    sourcePortSleep(25);
    phase = !phase;
    // A source-port environment supplies original virtual application edges.
    environment->tick(phase);
    if (environment->serverAvailable() && environment->hasClients())
      environment->clientTick(phase);
  }
  return 0;
}
void MeterManagerBase::updateClients() {
  if (!environment || !environment->serverAvailable())
    return;
  Core::Threads::ScopedLock guard(sourcePortLock);
  for (auto &clients : sourcePortClients)
    clients.empty();
  constexpr const char *tags[] = {"levl", "redu", "rtan"};
  for (int i = 0; i < environment->clientCount(); ++i) {
    const auto client = environment->clientAt(i);
    for (int tag = 0; tag < 3; ++tag)
      if (std::strstr(client.subscriptions, tags[tag]))
        sourcePortClients[tag + (client.external ? 3 : 0)].add(client.id);
  }
}
void MeterManagerBase::sendToClients(Core::FixedSizeVector<int, 100> &clients,
                                     UC::Event &event) {
  Core::Threads::ScopedLock guard(sourcePortLock);
  event.routeA = environment->sessionId();
  const int count = clients.count();
  for (int i = 0; i < count; ++i) {
    event.routeB = static_cast<std::uint32_t>(clients.at(i));
    network.sendEvent(event, 1);
  }
}
} // namespace Presonus
