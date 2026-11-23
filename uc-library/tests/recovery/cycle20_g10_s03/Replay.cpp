#include "presonus/panel/PanelComponent.hpp"

#include <array>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string_view>

using Presonus::Panel::ControlGroup;
using Presonus::Panel::PanelComponent;
using presonus::timing::DelayTimerAccess;
using presonus::timing::DelayTimerState;

namespace {
struct Services final : presonus::panel_port::Services {
  int activationCalls = 0;
  int groupCount() const override { unexpected(); }
  const ControlGroup &groupAt(int) const override { unexpected(); }
  std::uint32_t groupTag(const ControlGroup &) const override { unexpected(); }
  int controlCount(const ControlGroup &) const override { unexpected(); }
  void *controlAt(const ControlGroup &, int) const override { unexpected(); }
  void controlSlot10(void *, int, int) const override { unexpected(); }
  void componentSlot38() override { ++activationCalls; }
  void *findGroup(int) override { unexpected(); }
  void *byTag(void *, int) override { unexpected(); }
  void *castControlToLed(void *) override { unexpected(); }
  void setBlinkMode(void *, int) override { unexpected(); }

private:
  [[noreturn]] static void unexpected() {
    throw std::runtime_error("unexpected borrowed service call");
  }
};

class HookAccess : public PanelComponent {
public:
  using PanelComponent::PanelComponent;
  static auto activationSlot() { return &HookAccess::doActivate; }
  void invokeBaseActivation() { PanelComponent::doActivate(); }
};

void seedState(PanelComponent &panel, int seed) {
  auto &state = panel.portableState();
  const DelayTimerState timer{seed, seed + 50, seed + 7, 0.5f, seed != 0};
  DelayTimerAccess::set(state.encoderTimer, timer);
  DelayTimerAccess::set(state.buttonTimer, timer);
  state.active = seed != 0;
  state.embeddedHandlerState = {30, seed, -1, seed + 3, -seed};
}

bool sameTimer(const DelayTimerState &left, const DelayTimerState &right) {
  return left.start == right.start && left.duration == right.duration &&
         left.elapsed == right.elapsed && left.reciprocal == right.reciprocal &&
         left.executing == right.executing;
}

struct Snapshot {
  const presonus::panel_port::PanelCore *core;
  bool feedbackNeeded;
  const Presonus::Mixer::MixerComponentBase *mixer;
  const Presonus::Panel::PanelRegistrar *registrar;
  bool active;
  std::array<std::int32_t, 5> handler;
  DelayTimerState encoder, button;

  explicit Snapshot(const PanelComponent &panel)
      : core(&panel.portableState().component),
        feedbackNeeded(core->feedbackNeeded()),
        mixer(panel.portableState().mixer),
        registrar(panel.portableState().registrar),
        active(panel.portableState().active),
        handler(panel.portableState().embeddedHandlerState),
        encoder(DelayTimerAccess::get(panel.portableState().encoderTimer)),
        button(DelayTimerAccess::get(panel.portableState().buttonTimer)) {}

  bool operator==(const Snapshot &other) const {
    return core == other.core && feedbackNeeded == other.feedbackNeeded &&
           mixer == other.mixer && registrar == other.registrar &&
           active == other.active && handler == other.handler &&
           sameTimer(encoder, other.encoder) && sameTimer(button, other.button);
  }
};

int run(std::string_view route, int seed) {
  Services services;
  PanelComponent base(services);
  seedState(base, seed);
  bool unchanged = false;
  if (route == "direct") {
    HookAccess receiver(services);
    seedState(receiver, seed);
    const Snapshot before(receiver);
    receiver.invokeBaseActivation();
    unchanged = before == Snapshot(receiver);
  } else {
    const Snapshot before(base);
    if (route == "vtable")
      (base.*HookAccess::activationSlot())();
    else if (route == "activateAll")
      base.activateAll();
    else if (route == "start")
      base.start();
    else
      return 2;
    unchanged = before == Snapshot(base);
  }
  std::cout << unchanged << ' ' << services.activationCalls << '\n';
  return 0;
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  return run(argv[1], std::atoi(argv[2]));
}
