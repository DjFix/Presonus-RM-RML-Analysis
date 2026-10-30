#include "core/system/coredebug.h"
#include "presonus/uc/adapter_handler.hpp"
#include <cstring>

namespace presonus::uc {
bool CclAdapterServices::primary(AdapterIPAddress &address) const {
  return Core::Sockets::Network::getLocalIPAddress(address);
}
int CclAdapterServices::enumerate(AdapterIPAddress *addresses,
                                  int count) const {
  return Core::Sockets::Network::getLocalIPAddressList(addresses, count);
}
void CclAdapterServices::enumerate(
    Core::Vector<AdapterIPAddress> &addresses) const {
  Core::Sockets::Network::getLocalIPAddressList(addresses);
}
bool CclAdapterServices::hostname(Core::CStringBuffer<256> &name) const {
  return Core::Sockets::Network::getLocalHostname(name);
}
bool CclAdapterServices::format(Core::CStringBuffer<256> &text,
                                const AdapterIPAddress &address) const {
  return Core::Sockets::Network::getAddressString(text, address);
}
void CclAdapterServices::changed(const char *before, const char *after) const {
  // Intentional app diagnostic adaptation; original UCReportMessage routing
  // and severity/filter/report-recipient behavior are not reconstructed here.
  Core::DebugPrintf("IP address change detected from \"%s\" to \"%s\"\n",
                    before, after);
}
static std::int32_t signedBits(std::uint32_t bits) {
  std::int32_t value;
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}
} // namespace presonus::uc

namespace Presonus::UC {
void AdapterAddressList::copyFrom(const AdapterAddressList &other) {
  state_.count = 0;
  const int sourceCount = other.state_.count;
  for (int index = 0; index < sourceCount; ++index)
    if (state_.count < 10)
      state_.values[state_.count++] = other.state_.values[index];
}

bool AdapterAddressList::isEqual(const AdapterAddressList &other) const {
  if (state_.count != other.state_.count)
    return false;
  for (int index = 0; index < state_.count; ++index)
    if (state_.values[index] != other.state_.values[index])
      return false;
  return true;
}

void AdapterAddressList::toString(Core::CStringBuffer<256> &output) const {
  const presonus::uc::CclAdapterServices services;
  for (int index = 0; index < state_.count; ++index) {
    Core::CStringBuffer<256> address;
    services.format(address, state_.values[index]);
    if (!output.isEmpty())
      output.append(";");
    output.appendFormat("eth%d=%s", index, address.str());
  }
}

void AdapterHandler::invalidateAddressList() { state_.cacheValid = 0; }

AdapterAddressList *AdapterHandler::getAddressList(bool force) {
  if (state_.cacheValid && !force)
    return &state_.addresses;
  presonus::uc::AdapterAddressListState previousStorage;
  AdapterAddressList previous(presonus::uc::AdapterSourcePortTag{},
                              previousStorage);
  previous.copyFrom(state_.addresses);
  presonus::uc::AdapterIPAddress primary;
  if (state_.suspended ||
      (state_.services.primary(primary), state_.multiAddress == 0)) {
    state_.storage.values[0] = primary;
    state_.storage.count = 1;
  } else {
    state_.storage.count = state_.services.enumerate(
        state_.storage.values.data(),
        static_cast<int>(state_.storage.values.size()));
    bool found = false;
    for (int index = 0; index < state_.storage.count; ++index)
      if (state_.storage.values[index] == primary) {
        found = true;
        break;
      }
    if (!found && state_.storage.count < 10)
      state_.storage.values[state_.storage.count++] = primary;
  }
  state_.services.format(state_.primaryText, primary);
  state_.cacheValid = 1;
  if (previousStorage.count != 0 && !state_.addresses.isEqual(previous)) {
    state_.changed = 1;
    Core::CStringBuffer<256> before, after;
    previous.toString(before);
    state_.addresses.toString(after);
    state_.services.changed(before.str(), after.str());
  }
  return &state_.addresses;
}

bool AdapterHandler::isLocalHostAddress_threadSafe(const char *name) const {
  Core::CStringBuffer<256> text;
  if (!state_.suffix.isEmpty()) {
    state_.services.hostname(text);
    text.append(state_.suffix.str());
    return text.compare(name, false) == 0;
  }
  if (state_.multiAddress) {
    Core::Vector<presonus::uc::AdapterIPAddress> addresses;
    state_.services.enumerate(addresses);
    for (int index = 0; index < addresses.count(); ++index) {
      text.empty();
      state_.services.format(text, addresses.at(index));
      if (text.compare(name, false) == 0)
        return true;
    }
    return false;
  }
  presonus::uc::AdapterIPAddress primary;
  state_.services.primary(primary);
  state_.services.format(text, primary);
  return text.compare(name, false) == 0;
}

void AdapterHandler::getFirstLocalHostAddress_threadSafe(
    Core::CStringBuffer<256> &text) const {
  if (state_.suffix.isEmpty()) {
    presonus::uc::AdapterIPAddress primary;
    state_.services.primary(primary);
    state_.services.format(text, primary);
  } else {
    state_.services.hostname(text);
    text.append(state_.suffix.str());
  }
}

void AdapterHandler::process() {
  const auto previous = state_.processCounterBits;
  state_.processCounterBits = previous + 1U;
  state_.changed = 0;
  if (presonus::uc::signedBits(previous) >
      presonus::uc::signedBits(state_.refreshIntervalBits)) {
    state_.processCounterBits = 0;
    getAddressList(true);
  }
}
} // namespace Presonus::UC
