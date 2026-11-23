#include "presonus/panel/StormFrontPanelComponent.hpp"

#include <array>
#include <cstdint>
#include <cstdio>
#include <new>
#include <string_view>

using Presonus::Panel::Fat24FrontPanelComponent;
using Presonus::Panel::StormFrontPanelComponent;
using presonus::stormpanel_port::Handle;

extern "C" void destroyBaseVariant(StormFrontPanelComponent *) asm(
    "_ZN8Presonus5Panel24StormFrontPanelComponentD2Ev");

namespace {
unsigned events[3]{};
unsigned eventCount = 0;
std::uintptr_t receiver = 0;

void record(unsigned event) {
  if (eventCount < 3)
    events[eventCount] = event;
  ++eventCount;
}

struct BorrowedServices : presonus::stormpanel_port::Dependencies {
  unsigned calls = 0;
  void cleanup() override { ++calls; }
  void presetRecalled() override { ++calls; }
  void fatChannelUpdate() override { ++calls; }
  void fatMeterUpdate(Presonus::Mixer::ChannelComponent &) override { ++calls; }
  Handle findGroup(int) override {
    ++calls;
    return {};
  }
  Handle byTag(Handle, int) override {
    ++calls;
    return {};
  }
  void setControl(Handle, int, int) override { ++calls; }
  int count(Handle) override {
    ++calls;
    return {};
  }
  Handle at(Handle, int) override {
    ++calls;
    return {};
  }
  Handle asLED(Handle) override {
    ++calls;
    return {};
  }
  int tag(Handle) override {
    ++calls;
    return {};
  }
  void setBlinkMode(Handle, bool) override { ++calls; }
  void blinkLED(int, std::uint32_t, bool) override { ++calls; }
  Presonus::Panel::MixerLCD *constructLCD(std::size_t) override {
    ++calls;
    return nullptr;
  }
  void addBook(Presonus::Panel::MixerLCD *, std::uint32_t, int) override {
    ++calls;
  }
};

struct Observer : Core::Portable::ParamObserverBase {
  void paramChanged(Core::Portable::Parameter *, int message) override {
    if (message == Core::Portable::Parameter::kDestroyed)
      record(1);
  }
};

void observeBaseTeardown(Fat24FrontPanelComponent &panel,
                         Core::Portable::ParamObserverBase &observer,
                         unsigned parameterCount) {
  static const auto parameters = [] {
    std::array<Core::Portable::ParamInfo, 8> result{};
    for (unsigned index = 0; index < result.size(); ++index)
      result[index] = PARAM_TOGGLE(7810 + index, "teardown", 0, nullptr, 0);
    return result;
  }();
  auto &component = *panel.portableFrontState().panelParameters;
  component.addParameters(parameters.data(), parameterCount);
  component.getParameterByTag(parameters[0].tag)->addObserver(&observer);
}
} // namespace

extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __wrap__ZdlPv(void *pointer) noexcept {
  const bool tracked = reinterpret_cast<std::uintptr_t>(pointer) == receiver;
  __real__ZdlPv(pointer);
  if (tracked)
    record(2);
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string_view variant(argv[1]);
  const std::string_view count(argv[2]);
  if (count != "1" && count != "2" && count != "8")
    return 2;
  const unsigned parameterCount = count[0] - '0';
  BorrowedServices borrowed;
  Observer observer;
  if (variant == "D0") {
    auto *panel = new StormFrontPanelComponent(borrowed);
    receiver = reinterpret_cast<std::uintptr_t>(panel);
    Fat24FrontPanelComponent *base = panel;
    observeBaseTeardown(*base, observer, parameterCount);
    delete base;
  } else if (variant == "D1") {
    StormFrontPanelComponent panel(borrowed);
    receiver = reinterpret_cast<std::uintptr_t>(&panel);
    observeBaseTeardown(panel, observer, parameterCount);
  } else if (variant == "D2") {
    alignas(StormFrontPanelComponent) unsigned char
        storage[sizeof(StormFrontPanelComponent)];
    auto *panel = ::new (storage) StormFrontPanelComponent(borrowed);
    receiver = reinterpret_cast<std::uintptr_t>(panel);
    observeBaseTeardown(*panel, observer, parameterCount);
    destroyBaseVariant(panel);
  } else {
    return 2;
  }
  receiver = 0;
  std::printf("%u %u %u %u\n", eventCount, events[0], events[1],
              borrowed.calls);
}
