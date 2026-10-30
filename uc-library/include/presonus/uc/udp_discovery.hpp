#pragma once
#include "core/portable/coresingleton.h"
#include "core/public/corestringbuffer.h"
#include "core/public/corevector.h"
#include "presonus/uc/discovery_handler.hpp"
#include "presonus/uc/network_manager_services.hpp"
#include <cstdint>
namespace Presonus::UC {
class MulticastConnection;
class IDiscoveryReplyHandler;
class UDPDiscoveryEntry;
} // namespace Presonus::UC
namespace presonus::uc {
struct DiscoverySourcePortTag {};
class DiscoveryEntryOwnership;
// Independent initialized state, not the original entry declaration/layout.
struct DiscoveryEntryState {
  std::uint8_t flag0 = 0;
  std::uint8_t dirty = 0;
  std::uint8_t flag3 = 0;
  std::uint8_t flag4 = 0;
  Core::CStringBuffer<128> host;
  std::uint16_t port = 0;
  std::int32_t identifier = 0;
  std::uint32_t versionWord = 0;
  Core::CStringBuffer<64> displayName;
};
struct DiscoveryHandlerState {
  // Borrowed initialized entries: this partial interface never deletes entries.
  // Original shutdown/removeServer ownership is intentionally unreconstructed.
  Core::Vector<Presonus::UC::UDPDiscoveryEntry *> entries;
  // Required only by new owning lifecycle methods; old borrowed methods do not
  // use it.
  DiscoveryEntryOwnership *ownership = nullptr;
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
  UDPDiscoveryHandler(presonus::uc::DiscoverySourcePortTag,
                      presonus::uc::DiscoveryHandlerState &state)
      : state_(state) {}
  void setConnection(MulticastConnection *);
  bool startup(bool) override;
  void shutdown() override;
  void restartBrowsing() override;
  void removeServer(UDPDiscoveryEntry *);
  void unregisterServer(void *) override;
  // Unrecovered original slots remain pure: no production callback stubs.
  bool registerServer(void *&, const DiscoveryDescriptor &, int) override = 0;
  void processDiscovery() override = 0;
  void onMulticastEvent(const char *, unsigned short, unsigned short, int,
                        EventItem *) override = 0;
  virtual void setReplyHandler(IDiscoveryReplyHandler *);
  virtual bool startBrowsing();
  virtual void stopBrowsing();
  UDPDiscoveryEntry *find(const char *, unsigned short, int) const;
  UDPDiscoveryEntry *findLocal(int) const;
  virtual void updateServer(void *, const char *);

private:
  presonus::uc::DiscoveryHandlerState &state_;
};
} // namespace Presonus::UC
