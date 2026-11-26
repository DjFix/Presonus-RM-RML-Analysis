#pragma once
#include "core/portable/coresingleton.h"
#include "core/public/corestringbuffer.h"
#include "core/public/corevector.h"
#include "presonus/uc/discovery_attributes.hpp"
#include "presonus/uc/discovery_handler.hpp"
#include "presonus/uc/network_manager_services.hpp"
#include <cstdint>
#include <memory>
#include <optional>
namespace Presonus::UC {
class MulticastConnection;
class IDiscoveryReplyHandler;
class UDPDiscoveryEntry;
struct DiscoveryAliveEvent;
} // namespace Presonus::UC
namespace presonus::uc {
struct DiscoverySourcePortTag {};
class DiscoveryEntryOwnership;
// Independent initialized state, not the original entry declaration/layout.
struct DiscoveryEntryState {
  std::uint8_t flag0 = 0;
  std::uint8_t dirty = 0;
  std::uint8_t changed = 0;
  std::int64_t lastSeenMilliseconds = 0;
  std::uint32_t missedReplies = 0;
  std::uint8_t flag3 = 0;
  std::uint8_t flag4 = 0;
  Core::CStringBuffer<128> host;
  std::uint16_t port = 0;
  std::uint16_t replyPort = 0;
  Presonus::UC::DiscoveryAttributes attributes;
  std::int32_t identifier = 0;
  std::uint32_t versionWord = 0;
  Core::CStringBuffer<64> displayName;
};
struct DiscoveryHandlerState {
  // The vector owns storage for pointers. Application entry lifetimes belong
  // to the separately bound ownership provider.
  Core::Vector<Presonus::UC::UDPDiscoveryEntry *> entries;
  // Required only by new owning lifecycle methods; old borrowed methods do not
  // use it.
  DiscoveryEntryOwnership *ownership = nullptr;
  std::shared_ptr<DiscoveryEntryOwnership> ownedEntries;
  Presonus::UC::MulticastConnection *connection = nullptr;
  Presonus::UC::IDiscoveryReplyHandler *reply = nullptr;
  std::uint8_t browsing = 0;
  std::uint32_t counter28 = 0;
  std::uint32_t counter2c = 0;
};
} // namespace presonus::uc
namespace Presonus::UC {
class UDPDiscoveryEntry {
public:
  UDPDiscoveryEntry(presonus::uc::DiscoverySourcePortTag,
                    presonus::uc::DiscoveryEntryState &state)
      : state_(state) {}

  bool updateHostName(const char *);

private:
  friend class UDPDiscoveryHandler;
  presonus::uc::DiscoveryEntryState &state_;
};
class UDPDiscoveryHandler
    : public IDiscoveryHandler,
      public IMulticastReceiver,
      public Core::Portable::StaticSingleton<UDPDiscoveryHandler> {
public:
  UDPDiscoveryHandler();
  UDPDiscoveryHandler(const UDPDiscoveryHandler &other);
  ~UDPDiscoveryHandler();
  UDPDiscoveryHandler(presonus::uc::DiscoverySourcePortTag,
                      presonus::uc::DiscoveryHandlerState &state)
      : state_(state) {}
  void setConnection(MulticastConnection *);
  bool startup(bool) override;
  void shutdown() override;
  void restartBrowsing() override;
  void removeServer(UDPDiscoveryEntry *);
  void unregisterServer(void *) override;
  bool registerServer(void *&, const DiscoveryDescriptor &, int) override;
  void processDiscovery() override;
  void onMulticastEvent(const char *, unsigned short, unsigned short, int,
                        EventItem *) override;
  virtual void setReplyHandler(IDiscoveryReplyHandler *);
  virtual bool startBrowsing();
  virtual void stopBrowsing();
  UDPDiscoveryEntry *addServer(const char *, unsigned short, unsigned short,
                               const DiscoveryAliveEvent &);
  UDPDiscoveryEntry *find(const char *, unsigned short, int) const;
  UDPDiscoveryEntry *findLocal(int) const;
  virtual void updateServer(void *, const char *);

protected:
  presonus::uc::DiscoveryHandlerState &discoveryState() { return state_; }

private:
  // In-place storage for default construction. Tagged callers bind external
  // state and retain its lifetime. This is a portable source representation.
  std::optional<presonus::uc::DiscoveryHandlerState> ownedState_;
  presonus::uc::DiscoveryHandlerState &state_;
};
} // namespace Presonus::UC
