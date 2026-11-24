#include "presonus/panel/SPIControlGroup.hpp"
#include <iostream>

namespace {
class Capture final : public presonus::spi_port::Transfer {
public:
  int calls = 0;
  void submit(int, std::uint32_t, const std::uint8_t *, std::uint8_t *,
              int) override {
    ++calls;
  }
};
} // namespace

int main() {
  Capture capture;
  for (const bool dirty : {false, true}) {
    Presonus::Panel::SPIControlGroup group(17, 3, 4);
    group.attachTransport(11, capture);
    group.add(nullptr);
    group.markDirty(dirty);
    const auto tx = group.transmitted();
    const auto rx = group.received();
    group.close();
    const bool unchanged =
        group.isDirty() == dirty && group.count() == 1 &&
        group.at(0) == nullptr && group.payloadByteCount() == 4 &&
        group.transportDescriptor() == 11 && group.transmitted() == tx &&
        group.received() == rx && capture.calls == 0 &&
        presonus::panel_binding::ControlGroupAccess::groupId(group) == 17 &&
        presonus::panel_binding::ControlGroupAccess::ownsState(group);
    std::cout << unchanged << '\n';
  }
}
