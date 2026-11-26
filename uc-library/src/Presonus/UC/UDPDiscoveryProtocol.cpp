#include "core/public/coreuid.h"
#include "core/system/coretime.h"
#include "presonus/uc/MulticastDatagramProvider.hpp"
#include "presonus/uc/discovery_events.hpp"
#include "presonus/uc/discovery_ownership.hpp"
#include "presonus/uc/server.hpp"
#include "presonus/uc/source_default_factory.hpp"
#include "presonus/uc/udp_discovery.hpp"
#include <algorithm>
#include <cstring>
#include <stdexcept>
namespace Presonus::UC {
UDPDiscoveryEntry *
UDPDiscoveryHandler::addServer(const char *host, unsigned short port,
                               unsigned short replyPort,
                               const DiscoveryAliveEvent &event) {
  if (!state_.ownership)
    throw std::logic_error("Discovery entry ownership provider is required");
  auto *entry = state_.ownership->create();
  auto &value = state_.ownership->stateFor(entry);
  value.host = host ? host : "";
  value.port = port;
  value.replyPort = replyPort;
  value.identifier = static_cast<std::int32_t>(event.header.routeA);
  value.versionWord = event.versionBits;
  value.attributes.words[0] = event.versionBits;
  std::memcpy(value.attributes.words.data() + 1, &event.extensionBits, 16);
  for (int index = 0; index < 4; ++index)
    std::memcpy(value.attributes.strings[index].getBuffer(),
                event.strings[index].data(), 64);
  std::memcpy(value.displayName.getBuffer(), event.strings[3].data(), 64);
  if (!state_.entries.add(entry)) {
    state_.ownership->destroy(entry);
    throw std::bad_alloc();
  }
  DiscoveryDescriptor descriptor;
  descriptor.info.flags = static_cast<std::uint16_t>(value.versionWord);
  descriptor.addresses[0] = host;
  descriptor.ports = {port, replyPort};
  descriptor.word9 = event.header.routeA;
  Core::CStringBuffer<64> uidText;
  Core::UIDBytes uid;
  std::memcpy(&uid, value.attributes.words.data() + 1, 16);
  const unsigned char zero[16]{};
  if (std::memcmp(&uid, zero, 16) != 0)
    uid.toCString(uidText.getBuffer(), 64, 0);
  descriptor.info.strings = {value.attributes.strings[0].str(),
                             value.attributes.strings[1].str(), uidText.str(),
                             value.attributes.strings[2].str()};
  descriptor.addresses[1] = value.displayName.str();
  state_.reply->onServerAdded(entry, descriptor);
  return entry;
}
namespace {
std::int64_t discoveryTime() {
  return Core::SystemClock::getTime() /
         static_cast<std::int64_t>(Core::SystemClock::getFrequency() / 1000);
}
DiscoveryAliveEvent aliveFor(const presonus::uc::DiscoveryEntryState &value) {
  DiscoveryAliveEvent event;
  event.header = {17473, 292, static_cast<std::uint32_t>(value.identifier), 0};
  event.versionBits = value.versionWord;
  std::memcpy(&event.extensionBits, value.attributes.words.data() + 1, 16);
  for (int i = 0; i < 4; ++i)
    std::memcpy(event.strings[i].data(), value.attributes.strings[i].str(), 64);
  // These fields have existing live storage; the attributes are an initial
  // metadata snapshot, not a second owner of the current name/version.
  std::memcpy(event.strings[3].data(), value.displayName.str(), 64);
  return event;
}
template <class Action>
bool withAlive(DiscoveryAliveEvent &event, Action action) {
  auto &codec =
      presonus::uc::DefaultFactoryProvider<DiscoveryAliveEventClass>::get();
  codec.bind(event);
  struct Unbind {
    decltype(codec) provider;
    DiscoveryAliveEvent &value;
    ~Unbind() { provider.unbind(value); }
  } unbind{codec, event};
  return action(event.header);
}
} // namespace
bool UDPDiscoveryHandler::registerServer(void *&identity,
                                         const DiscoveryDescriptor &descriptor,
                                         int flags) {
  if (!state_.ownership)
    throw std::logic_error("Discovery entry ownership provider is required");
  auto *entry = state_.ownership->create();
  auto &value = state_.ownership->stateFor(entry);
  value.flag0 = 1;
  value.dirty = 1;
  value.flag3 = flags & 1;
  value.identifier = static_cast<std::int32_t>(descriptor.word9);
  presonus::uc::sourceAdapterSingleton();
  Core::UIDBytes uid{};
  uid.fromCString(descriptor.info.strings[2], 0);
  value.versionWord = static_cast<std::uint16_t>(descriptor.info.flags);
  const unsigned char zero[16]{};
  if (std::memcmp(&uid, zero, 16) != 0)
    value.versionWord |= 0x80000000U;
  value.attributes.words[0] = value.versionWord;
  std::memcpy(value.attributes.words.data() + 1, &uid, 16);
  const char *strings[] = {descriptor.info.strings[0],
                           descriptor.info.strings[1],
                           descriptor.info.strings[3], descriptor.addresses[1]};
  for (int i = 0; i < 4; ++i)
    value.attributes.strings[i] = strings[i] ? strings[i] : "";
  value.displayName = strings[3] ? strings[3] : "";
  state_.counter28 = state_.counter2c = 0;
  if (!state_.entries.add(entry)) {
    state_.ownership->destroy(entry);
    throw std::bad_alloc();
  }
  identity = entry;
  return true;
}
void UDPDiscoveryHandler::onMulticastEvent(const char *host,
                                           unsigned short port,
                                           unsigned short replyPort,
                                           int locality, EventItem *item) {
  auto &event = item->getData();
  if (locality != 1)
    return;
  auto *entry = find(host, port, static_cast<int>(event.routeA));
  if (event.type == 17473 && state_.browsing) {
    auto *typed =
        dynamic_cast<presonus::uc::TypedEventItem<DiscoveryAliveEvent> *>(item);
    if (!typed)
      throw std::invalid_argument("Discovery alive requires actual typed item");
    if (!entry)
      entry = addServer(host, port, replyPort, typed->value);
    auto &value = entry->state_;
    value.lastSeenMilliseconds = discoveryTime();
    value.missedReplies = 0;
    const auto version = (typed->value.versionBits >> 16) & 255U;
    if (((value.versionWord >> 16) & 255U) != version) {
      value.versionWord = (value.versionWord & ~0xff0000U) | (version << 16);
      entry->updateHostName(typed->value.strings[3].data());
      state_.reply->onServerChanged(entry, value.displayName.str());
    }
  } else if (event.type == 17484) {
    if (entry)
      removeServer(entry);
  } else if (event.type == 17489) {
    auto *local = findLocal(static_cast<int>(event.routeB));
    if (!local)
      return;
    auto alive = aliveFor(local->state_);
    presonus::uc::AdapterIPAddress address;
    Core::Sockets::Network::getAddressFromString(address, host);
    address.port = replyPort;
    presonus::uc::MulticastDatagramProvider provider(*state_.connection);
    withAlive(alive, [&](const Event &value) {
      return provider.sendTo(address, value);
    });
  } else if (entry) {
    entry->state_.lastSeenMilliseconds = discoveryTime();
    entry->state_.missedReplies = 0;
  }
}
void UDPDiscoveryHandler::processDiscovery() {
  const auto now = discoveryTime();
  const std::uint64_t last =
      state_.counter28 | (static_cast<std::uint64_t>(state_.counter2c) << 32);
  if (now - static_cast<std::int64_t>(last) <= 2499)
    return;
  state_.counter28 = static_cast<std::uint32_t>(now);
  state_.counter2c = static_cast<std::uint64_t>(now) >> 32;
  Core::Vector<UDPDiscoveryEntry *> expired;
  const int count = state_.entries.count();
  for (int index = 0; index < count; ++index) {
    auto *entry = state_.entries.at(index);
    auto &value = entry->state_;
    if (value.flag0) {
      if (value.dirty) {
        state_.reply->onRegistrationCompleted(entry);
        value.dirty = 0;
      }
      if (value.changed) {
        state_.reply->onServerChanged(entry, value.displayName.str());
        value.changed = 0;
      }
      if (!value.flag3 && !value.flag4) {
        auto alive = aliveFor(value);
        withAlive(alive, [&](const Event &event) {
          return state_.connection->sendEvent(event);
        });
      }
    } else {
      auto &adapter = presonus::uc::sourceAdapterSingleton();
      const bool same =
          value.host.compare(adapter.sourcePortState().primaryText.str(),
                             true) == 0;
      if (now - value.lastSeenMilliseconds < (same ? 2500 : 7500))
        continue;
      if (value.missedReplies >= static_cast<unsigned>(same ? 1 : 3)) {
        expired.add(entry);
        continue;
      }
      presonus::uc::AdapterIPAddress address;
      Core::Sockets::Network::getAddressFromString(address, value.host.str());
      address.port = value.replyPort;
      Event query{17489, 16, 0, static_cast<std::uint32_t>(value.identifier)};
      presonus::uc::MulticastDatagramProvider provider(*state_.connection);
      if (provider.sendTo(address, query))
        ++value.missedReplies;
    }
  }
  for (int index = 0; index < expired.count(); ++index)
    removeServer(expired.at(index));
}
} // namespace Presonus::UC
