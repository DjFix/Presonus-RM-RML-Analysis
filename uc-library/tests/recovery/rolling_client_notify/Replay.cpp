#include "presonus/uc/ClientComponent.hpp"
#include "presonus/uc/message_attributes.hpp"
#include <array>
#include <iostream>
#include <optional>
#include <string>

namespace {
std::optional<std::string> snapshot(const char *value) {
  if (value)
    return std::string(value);
  return std::nullopt;
}
} // namespace

int main() {
  using namespace Presonus::UC;
  for (const char *name :
       {"", "client", "surface", "test", "port", "rack", "transport"}) {
    ClientComponent receiver(name);
    MessageAttributes payload(name);
    payload.setSource("replay-source");
    payload.setURL("/uc/test");
    const std::array before{snapshot(payload.getID()),
                            snapshot(payload.getSource()),
                            snapshot(payload.getURL())};
    const auto opaque =
        presonus::uc::MessageAttributesPortAccess::opaqueState(payload);
    const auto parent = receiver.getParent();
    const auto children = receiver.countChildren();
    const auto parameters = receiver.countParameters();
    // Portable call through the typed receiver and the const payload reference.
    auto method = &ClientComponent::notify;
    (receiver.*method)(payload);
    const std::array after{snapshot(payload.getID()),
                           snapshot(payload.getSource()),
                           snapshot(payload.getURL())};
    const bool unchanged =
        before == after && receiver.getName() == name &&
        parent == receiver.getParent() &&
        children == receiver.countChildren() &&
        parameters == receiver.countParameters() &&
        opaque ==
            presonus::uc::MessageAttributesPortAccess::opaqueState(payload);
    if (!unchanged)
      return 1;
    std::cout << unchanged << '\n';
  }
}
