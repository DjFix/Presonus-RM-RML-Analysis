#pragma once
#include "core/network/corenetwork.h"
#include "core/public/corestringbuffer.h"
#include <array>
#include <cstdint>
#include <memory>

namespace presonus::uc {
struct AdapterSourcePortTag {};
// Actual upstream SocketTypes::IPAddress is used internally. It is not a fake
// legacy Core::Sockets::IPAddress class and does not preserve that old
// mangling.
using AdapterIPAddress = Core::Sockets::SocketTypes::IPAddress;
struct AdapterAddressListState {
  // Initialized-state contract: count is0..10; all queried entries are live
  // genuine IPAddress values. Malformed unchecked original arrays are excluded.
  std::array<AdapterIPAddress, 10> values;
  int count = 0;
};
class CclAdapterServices {
public:
  bool primary(AdapterIPAddress &) const;
  int enumerate(AdapterIPAddress *, int) const;
  void enumerate(Core::Vector<AdapterIPAddress> &) const;
  bool hostname(Core::CStringBuffer<256> &) const;
  bool format(Core::CStringBuffer<256> &, const AdapterIPAddress &) const;
  void changed(const char *, const char *) const;
};
struct AdapterHandlerState;
} // namespace presonus::uc

namespace Presonus::UC {
class AdapterAddressList {
public:
  AdapterAddressList(presonus::uc::AdapterSourcePortTag,
                     presonus::uc::AdapterAddressListState &state)
      : state_(state) {}
  void copyFrom(const AdapterAddressList &);
  bool isEqual(const AdapterAddressList &) const;
  void toString(Core::CStringBuffer<256> &) const;

private:
  presonus::uc::AdapterAddressListState &state_;
};
} // namespace Presonus::UC

namespace presonus::uc {
// Independent initialized source-port configuration/cache, not original fields.
struct AdapterHandlerState {
  explicit AdapterHandlerState(CclAdapterServices &provider)
      : services(provider), addresses(AdapterSourcePortTag{}, storage) {}
  AdapterHandlerState(const AdapterHandlerState &) = delete;
  AdapterHandlerState &operator=(const AdapterHandlerState &) = delete;
  CclAdapterServices &services;
  AdapterAddressListState storage;
  Presonus::UC::AdapterAddressList addresses;
  Core::CStringBuffer<32> suffix;
  Core::CStringBuffer<256> primaryText;
  std::uint8_t multiAddress = 0;
  std::uint8_t suspended = 0;
  std::uint8_t cacheValid = 0;
  std::uint8_t changed = 0;
  std::uint32_t refreshIntervalBits = 1000;
  std::uint32_t processCounterBits = 0;
};
} // namespace presonus::uc

namespace Presonus::UC {
class AdapterHandler {
public:
  // Owning initialized source port; storage is independent of original ARM
  // layout.
  AdapterHandler();
  ~AdapterHandler();
  AdapterHandler(presonus::uc::AdapterSourcePortTag,
                 presonus::uc::AdapterHandlerState &state);
  AdapterHandler(const AdapterHandler &) = delete;
  AdapterHandler &operator=(const AdapterHandler &) = delete;
  // Independent source-port access, not a recovered original ELF interface.
  presonus::uc::AdapterHandlerState &sourcePortState() { return state_; }
  const presonus::uc::AdapterHandlerState &sourcePortState() const {
    return state_;
  }
  void invalidateAddressList();
  AdapterAddressList *getAddressList(bool);
  bool isLocalHostAddress_threadSafe(const char *) const;
  void getFirstLocalHostAddress_threadSafe(Core::CStringBuffer<256> &) const;
  void process();
  // fixUDPAddress/isLocalIPAddress are deliberately deferred: original
  // Core::Sockets::IPAddress differs from CCL SocketTypes::IPAddress encoding.

private:
  struct OwnedState;
  std::unique_ptr<OwnedState> owned_;
  presonus::uc::AdapterHandlerState &state_;
};
} // namespace Presonus::UC

namespace presonus::uc {
// Independent source API backed by the pinned CCL StaticSingleton provider.
Presonus::UC::AdapterHandler &sourceAdapterSingleton();
} // namespace presonus::uc
