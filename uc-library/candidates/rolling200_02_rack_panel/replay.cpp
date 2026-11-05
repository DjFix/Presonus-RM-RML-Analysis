#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/RackPanelComponent.hpp"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <memory>
#include <string>
#include <time.h>
using namespace Core::Portable;
namespace {
std::int64_t rawTime;
int clockCalls = 0, resets = 0, updateCalls = 0;
struct Tree : Component {
  void add(int tag) {
    auto *info = new ParamInfo{};
    info->type = ParamInfo::kFloat;
    info->maxValue = 1;
    info->tag = tag;
    paramList.add(new NumericParam(*info, true));
  }
};
struct Observer : ParamObserverBase {
  std::vector<int> trace;
  void paramChanged(Parameter *p, int message) override {
    assert(message == Parameter::kChanged);
    trace.push_back(p->getTag());
  }
};
struct Dependencies : presonus::rackpanel_port::Dependencies {
  Tree monitor;
  std::vector<presonus::rackpanel_port::Channel> channelList;
  presonus::panel_binding::ControlGroupState state;
  Presonus::Panel::ControlGroup controls{state};
  std::vector<std::unique_ptr<Presonus::Panel::LEDControl>> leds;
  std::vector<int> blinkModes;
  int clients = 0;
  Dependencies() {
    state.tagOf = [](void *, const Presonus::Panel::Control *p) {
      return presonus::panel::ControlAccess::tag(
          *const_cast<Presonus::Panel::Control *>(p));
    };
    for (int tag : {100, 101}) {
      leds.push_back(std::make_unique<Presonus::Panel::LEDControl>(tag, 0, -1));
      controls.add(leds.back().get());
    }
  }
  Presonus::Panel::ControlGroup &group(int id) override {
    assert(id == 0);
    return controls;
  }
  Component &monitorParameters() override { return monitor; }
  const std::vector<presonus::rackpanel_port::Channel> &
  channels() const override {
    return channelList;
  }
  int numClients() const override { return clients; }
  void removeDelegate(Presonus::Panel::RackPanelComponent &) override {}
  void blink(Presonus::Panel::LEDControl &led, int mode) override {
    blinkModes.push_back(mode);
    presonus::rackpanel_port::Dependencies::blink(led, mode);
  }
};
struct Target : Presonus::Panel::RackPanelComponent {
  using RackPanelComponent::RackPanelComponent;
  void add(int tag) {
    auto *info = new ParamInfo{};
    info->type = ParamInfo::kFloat;
    info->maxValue = 1;
    info->tag = tag;
    paramList.add(new NumericParam(*info, true));
  }
};
} // namespace
extern "C" void observedUpdate(void *) asm(
    "_ZN8Presonus5Panel18RackPanelComponent17updatePanelStatusEv");
extern "C" void __cyg_profile_func_enter(void *function, void *) {
  if (function == reinterpret_cast<void *>(observedUpdate))
    ++updateCalls;
}
extern "C" void __cyg_profile_func_exit(void *, void *) {}
extern "C" int __wrap_clock_gettime(clockid_t clock, timespec *value) {
  assert(clock == CLOCK_MONOTONIC);
  ++clockCalls;
  value->tv_sec = rawTime / 1000000000;
  value->tv_nsec = rawTime % 1000000000;
  return 0;
}
extern "C" void realReset(Presonus::Mixer::MixerComponentBase *) asm(
    "__real__ZN8Presonus5Mixer18MixerComponentBase18resetPermissionsPWEv");
extern "C" void wrapReset(Presonus::Mixer::MixerComponentBase *m) asm(
    "__wrap__ZN8Presonus5Mixer18MixerComponentBase18resetPermissionsPWEv");
extern "C" void wrapReset(Presonus::Mixer::MixerComponentBase *m) {
  ++resets;
  realReset(m);
}
int main(int argc, char **argv) {
  assert(argc >= 2);
  int method = std::stoi(argv[1]);
  Dependencies deps;
  Target target(deps);
  Presonus::Mixer::MixerComponentBase mixer;
  target.mixer = &mixer;
  if (method == 1) {
    // Actual clientsChanged effects must agree with the already implemented
    // status method for all status branches and representative client counts.
    target.add(2);
    target.add(3);
    for (int status : {-1, 0, 1, 2, 3, 4}) {
      for (int clients : {0, 1, 8}) {
        target.panelStatus = status;
        deps.clients = clients;
        deps.blinkModes.clear();
        const int previousCalls = updateCalls;
        target.clientsChanged();
#ifdef RACK_PANEL_INSTRUMENTED_REPLAY
        assert(updateCalls == previousCalls + 1);
#else
        (void)previousCalls;
#endif
        const auto blue = target.getParameterByTag(2)->getValue();
        const auto red = target.getParameterByTag(3)->getValue();
        const auto blinks = deps.blinkModes;
        std::cout << status << " " << clients << " " << blue << " " << red
                  << " " << blinks.at(0) << " " << blinks.at(1) << "\n";
        deps.blinkModes.clear();
        target.updatePanelStatus();
        assert(target.getParameterByTag(2)->getValue() == blue);
        assert(target.getParameterByTag(3)->getValue() == red);
        assert(deps.blinkModes == blinks && blinks.size() == 2);
      }
    }
    std::cout << "clients-provider 18\n";
  } else if (method == 2) {
    assert(argc == 5);
    target.permissionFlags = std::stoul(argv[2]);
    rawTime = std::stoll(argv[3]);
    std::uint64_t startup = std::stoull(argv[4]);
    target.permissionStartupMilliseconds = &startup;
    clockCalls = resets = 0;
    target.checkPermissionsPWReset();
    std::cout << target.permissionFlags << ' ' << clockCalls << ' ' << resets
              << ' ' << startup << '\n';
  } else if (method == 3) {
    Tree parameters;
    Observer observer;
    const std::vector<int> tags{7, 8, 9, 10, 11, 12, 13, 15, 14, 19, 28, 20};
    mixer.cascadeParameters = &parameters;
    for (int tag : tags) {
      parameters.add(tag);
      parameters.getParameterByTag(tag)->addObserver(&observer);
    }
    target.forceCascadeGlobalParamUpdate();
    for (int tag : observer.trace)
      std::cout << "changed " << tag << '\n';
    for (int tag : tags)
      parameters.getParameterByTag(tag)->removeObserver(&observer);
  } else if (method == 4) {
    target.help();
  } else if (method == 5) {
    // Both instances borrow the same process timestamp. Changing the timestamp
    // after binding affects both instances without rebinding or copying.
    Target other(deps);
    std::uint64_t startup = 2000;
    target.permissionStartupMilliseconds = other.permissionStartupMilliseconds =
        &startup;
    target.mixer = other.mixer = &mixer;
    rawTime = 2500000000;
    target.checkPermissionsPWReset();
    std::cout << target.permissionFlags << " ";
    other.checkPermissionsPWReset();
    std::cout << other.permissionFlags << " ";
    assert(target.permissionFlags == 0 && other.permissionFlags == 0);
    startup = 1000;
    target.checkPermissionsPWReset();
    std::cout << target.permissionFlags << " ";
    other.checkPermissionsPWReset();
    std::cout << other.permissionFlags << "\n";
    assert(target.permissionFlags == 16 && other.permissionFlags == 16);
    assert(startup == 1000);

  } else {
    return 2;
  }
}
