#include "presonus/surface/DAWMixerHandler.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string_view>

using Presonus::Surface::DAWMixerHandler;
using namespace Core::Portable;

namespace {
void *receiver;
int receiverDeletes;
int order;
int deletionOrder;

void require(bool condition) {
  if (!condition)
    std::abort();
}

class Dependencies final : public presonus::surface::DAWMixerDependencies {
public:
  Presonus::DAWChannel *focusChannel() override { return nullptr; }
  Presonus::DAWChannel *mainChannel() override { return nullptr; }
  int selectedMix() const override { return 33; }
  bool showStripMeters() const override { return false; }
  Component *component(Presonus::DAWChannel *) const override {
    return nullptr;
  }
  Presonus::DAWDeviceFolder *folder(Presonus::DAWChannel *,
                                    bool) const override {
    return nullptr;
  }
  int usedCount(Presonus::DAWDeviceFolder *) const override { return 0; }
  Component *slot(Presonus::DAWDeviceFolder *, int) const override {
    return nullptr;
  }
  const char *channelType(Presonus::DAWChannel *) const override {
    return nullptr;
  }
  void connect(const char *, Parameter *, const char *, bool) override {}
  void assignChannels() override {}
  void assignControlLinkTargets() override {}
  void assignSelectedChannelTargets() override {}
  void assignFlexStrip() override {}
};

class DestructionObserver final : public ParamObserverBase {
public:
  std::array<int, 4> tags{};
  int count = 0;
  int lastOrder = 0;

  void paramChanged(Parameter *parameter, int message) override {
    if (message == Parameter::kDestroyed) {
      require(count < static_cast<int>(tags.size()));
      tags[count++] = parameter->getTag();
      lastOrder = ++order;
      parameter->removeObserver(this);
    }
  }
};

constexpr ParamInfo parameters[] = {
    PARAM_TOGGLE(0, "zero", 1, nullptr, 0),
    PARAM_TOGGLE(1, "one", 1, nullptr, 0),
    PARAM_TOGGLE(2, "two", 1, nullptr, 0),
    PARAM_TOGGLE(3, "three", 1, nullptr, 0),
};

void populate(ParamList &list, int count, DestructionObserver &observer) {
  for (int index = 0; index < count; ++index) {
    auto *parameter = list.add(parameters[index]);
    parameter->addObserver(&observer);
    require(parameter->getValue() == 1.f);
  }
}
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *address) {
  if (receiver && address == receiver) {
    ++receiverDeletes;
    deletionOrder = ++order;
  }
  __real__ZdlPv(address);
}
extern "C" void completeDestructor(DAWMixerHandler *) asm(
    "_ZN8Presonus7Surface15DAWMixerHandlerD1Ev");
extern "C" void baseDestructor(DAWMixerHandler *) asm(
    "_ZN8Presonus7Surface15DAWMixerHandlerD2Ev");
extern "C" void deletingDestructor(DAWMixerHandler *) asm(
    "_ZN8Presonus7Surface15DAWMixerHandlerD0Ev");

int main(int argc, char **argv) {
  require(argc == 2);
  const std::string_view variant(argv[1]);
  require(variant == "D1" || variant == "D2" || variant == "D0");
  const bool deleting = variant == "D0";
  const auto destroy = deleting          ? deletingDestructor
                       : variant == "D1" ? completeDestructor
                                         : baseDestructor;

  for (const int count : {0, 1, 4}) {
    DestructionObserver reference;
    {
      ParamList standalone;
      populate(standalone, count, reference);
    }
    require(reference.count == count);

    for (const bool owned : {true, false}) {
      DestructionObserver observer;
      {
        ParamList borrowed;
        Dependencies dependencies;
        presonus::surface::DAWMixerState state;
        state.clientPresent = true;
        receiverDeletes = deletionOrder = order = 0;
        receiver = ::operator new(sizeof(DAWMixerHandler));
        auto *handler =
            owned ? new (receiver) DAWMixerHandler(dependencies, state)
                  : new (receiver)
                        DAWMixerHandler(dependencies, state, borrowed);
        auto &automation = handler->automationParameters();
        require(owned ? &automation != &borrowed : &automation == &borrowed);
        populate(automation, count, observer);
        require(handler->getSelectedMix() == 33 &&
                handler->getSelectedMeterMode() == -1 &&
                handler->shouldShowStripEncodersAsMeters() &&
                handler->canActivate() &&
                std::strcmp(handler->getName(), "dawmixer") == 0);
        handler->syncAutomationParams(nullptr);
        for (int index = 0; index < count; ++index)
          require(automation.byTag(index)->getValue() == 0.f);

        destroy(handler);
        require(receiverDeletes == static_cast<int>(deleting));
        require(state.clientPresent);
        require(observer.count == (owned ? count : 0));
        if (owned) {
          require(observer.tags == reference.tags);
          if (deleting && count)
            require(observer.lastOrder < deletionOrder);
        } else {
          require(borrowed.count() == count);
          for (int index = 0; index < count; ++index)
            require(borrowed.byTag(index)->getValue() == 0.f);
        }
        auto *allocation = receiver;
        receiver = nullptr;
        if (!deleting)
          ::operator delete(allocation);
      }
      require(observer.count == reference.count &&
              observer.tags == reference.tags);
      std::cout << variant << ' ' << (owned ? "owned" : "borrowed") << ' '
                << count << ' ' << receiverDeletes << '\n';
    }
  }
}
