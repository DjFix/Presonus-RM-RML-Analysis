#include "presonus/MeterManagerBase.hpp"
#include "presonus/MeterMaid.hpp"
#include <cstring>
#include <stdexcept>
#include <type_traits>

namespace Presonus {
void MeterManagerBase::deleteAll(Core::Vector<MeterMaid *> &roster) {
  const int count = roster.count();
  for (int i = 0; i < count; ++i)
    delete roster.at(i);
  roster.removeAll();
}

void MeterManagerBase::processMeters(bool) {}
void MeterManagerBase::sendUCNETMeters(bool) {}
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

namespace presonus::meter {
Presonus::UC::Event &
MutableMeterOrigins::resolve(Presonus::UC::MeterEvent &view) const {
  auto found = owners_.find(&view.header);
  if (found == owners_.end())
    throw std::invalid_argument("unbound mutable meter origin");
  return std::visit(
      [&](const auto &owned) -> Presonus::UC::Event & {
        auto *owner = owned.get();
        using Owner = std::remove_pointer_t<decltype(owner)>;
        auto payload = std::get_if<const Owner *>(&view.payload);
        if (!payload || *payload != owner || &owner->header != &view.header ||
            &owner->keyBits != &view.keyBits ||
            &owner->source != &view.source || &owner->count != &view.count ||
            &owner->recordCount != &view.recordCount ||
            &owner->reserved25 != &view.reserved25 ||
            &owner->records != &view.records ||
            owner->data.data() != view.data ||
            owner->data.size() != view.dataCapacity ||
            Owner::sampleWidth != view.sampleWidth)
          throw std::invalid_argument("mismatched mutable meter origin");
        return owner->header;
      },
      found->second);
}
} // namespace presonus::meter
namespace Presonus {
void MeterManagerBase::sendToExternalClients(
    Core::FixedSizeVector<int, 100> &clients, UC::MeterEvent &event,
    int selector) {
  if (clients.count() == 0)
    return;
  if (!external_ || !mutableOrigins_ || !envelopeCodec_)
    throw std::logic_error("external meter providers not configured");
  auto &header = mutableOrigins_->resolve(event);
  header.routeB = 0;
  header.routeA = 0;
  external_->sendEvent(header);
  UC::MeterEvent8 envelope{};
  envelope.header.type = 19778;
  envelope.header.reserved04 = 1268;
  envelope.keyBits = 0x6d726570;
  envelope.records[0].a = static_cast<unsigned short>(selector);
  envelope.recordCount = 1;
  envelopeCodec_->bind(envelope);
  struct Unbind {
    presonus::uc::Meter8FactoryCodec &codec;
    UC::MeterEvent8 &event;
    ~Unbind() { codec.unbind(event); }
  } unbind{*envelopeCodec_, envelope};
  sendToClients(clients, envelope.header);
}
} // namespace Presonus
