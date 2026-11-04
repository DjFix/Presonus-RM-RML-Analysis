#include "presonus/ColorMapping.hpp"
#include "presonus/DisplayCommandList.hpp"
#include "presonus/SpectrumPainter.hpp"
#include "presonus/color/MixerColorConverter.hpp"
#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string>
using E = Presonus::Surface::SLMixerHandler;
using X = presonus::surface::SLMixerEncoderAccess;
using A = presonus::surface::PageObserverAccess;
namespace {
void *watched[12]{};
int freed[32]{}, total = 0, removals = 0;
bool capture = false;
int cleanup[64]{}, cleanupTotal = 0;
void event(int id) {
  if (capture) {
    if (cleanupTotal >= 64)
      std::abort();
    cleanup[cleanupTotal++] = id;
  }
}
void observeFree(void *p) {
  if (capture && p)
    for (int i = 0; i < 12; ++i)
      if (p == watched[i]) {
        if (total >= 32)
          std::abort();
        freed[total++] = i;
        event(i);
      }
}
} // namespace
void operator delete(void *p) noexcept {
  observeFree(p);
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
void operator delete[](void *p) noexcept { ::operator delete(p); }
void operator delete[](void *p, std::size_t) noexcept { ::operator delete(p); }
extern "C" void
realRemove(Core::Portable::Parameter *, Core::Portable::IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrappedRemove(
    Core::Portable::Parameter *,
    Core::Portable::IParamObserver
        *) asm("__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
               "14IParamObserverE");
extern "C" void wrappedRemove(Core::Portable::Parameter *p,
                              Core::Portable::IParamObserver *o) {
  if (capture) {
    ++removals;
    event(10);
  }
  realRemove(p, o);
}

extern "C" void
realTimer(Presonus::DelayTimer *) asm("__real__ZN8Presonus10DelayTimerD1Ev");
extern "C" void
wrappedTimer(Presonus::DelayTimer *) asm("__wrap__ZN8Presonus10DelayTimerD1Ev");
extern "C" void wrappedTimer(Presonus::DelayTimer *p) {
  event(6);
  realTimer(p);
}
extern "C" void realEq(Presonus::Surface::EQPageComponent *,
                       Presonus::Surface::EQPageComponent::IObserver
                           *) asm("__real__"
                                  "ZN8Presonus7Surface15EQPageComponent14remove"
                                  "ObserverEPNS1_9IObserverE");
extern "C" void wrappedEq(Presonus::Surface::EQPageComponent *,
                          Presonus::Surface::EQPageComponent::IObserver
                              *) asm("__wrap__"
                                     "ZN8Presonus7Surface15EQPageComponent14rem"
                                     "oveObserverEPNS1_9IObserverE");
extern "C" void wrappedEq(Presonus::Surface::EQPageComponent *p,
                          Presonus::Surface::EQPageComponent::IObserver *o) {
  event(7);
  realEq(p, o);
}
extern "C" void realGeq(Presonus::Surface::GeqPageComponent *,
                        Presonus::Surface::GeqPageComponent::IObserver
                            *) asm("__real__"
                                   "ZN8Presonus7Surface16GeqPageComponent14remo"
                                   "veObserverEPNS1_9IObserverE");
extern "C" void wrappedGeq(Presonus::Surface::GeqPageComponent *,
                           Presonus::Surface::GeqPageComponent::IObserver
                               *) asm("__wrap__"
                                      "ZN8Presonus7Surface16GeqPageComponent14r"
                                      "emoveObserverEPNS1_9IObserverE");
extern "C" void wrappedGeq(Presonus::Surface::GeqPageComponent *p,
                           Presonus::Surface::GeqPageComponent::IObserver *o) {
  event(8);
  realGeq(p, o);
}
extern "C" void
realDigital(E *, Core::Portable::Parameter *, Core::Portable::Parameter *) asm(
    "__real__"
    "ZN8Presonus7Surface14SLMixerHandler16setDigitalParamsEPN4Core8Portable9Par"
    "ameterES5_");
extern "C" void
wrappedDigital(E *, Core::Portable::Parameter *,
               Core::Portable::Parameter
                   *) asm("__wrap__"
                          "ZN8Presonus7Surface14SLMixerHandler16setDigitalParam"
                          "sEPN4Core8Portable9ParameterES5_");
extern "C" void wrappedDigital(E *p, Core::Portable::Parameter *a,
                               Core::Portable::Parameter *b) {
  event(9);
  realDigital(p, a, b);
}

class Fixture : public E {
public:
  Fixture() = default;
  Fixture(Presonus::Surface::EQPageComponent *eq,
          Presonus::Surface::GeqPageComponent *geq,
          Presonus::IColorConverter *color)
      : E(OwnedLifecycle{}, eq, geq, color) {}
  void updateConnections() override { std::abort(); }
  void initialize(Core::Portable::Component *) override { std::abort(); }
  void setController(Presonus::IMappingController *) override { std::abort(); }
  void updatePanEncoderConnection() override { std::abort(); }
  bool getParamFocusInfo(FocusInfo &, Core::Portable::Parameter *) override {
    std::abort();
  }
  void paramChanged(Core::Portable::Parameter *, int) override { std::abort(); }
  void onSelectionChanged() override { std::abort(); }
  void onObjectChanged(ObjectChangeMessage) override { std::abort(); }
  void onComponentReplaced(const ReplaceArgs &) override { std::abort(); }
  void onEqEncoderModeChanged() override { std::abort(); }
  void onGeqScrollOffsetChanged() override { std::abort(); }
};
extern "C" void destroyD0(E *) asm("_ZN8Presonus7Surface14SLMixerHandlerD0Ev");
extern "C" void destroyD1(E *) asm("_ZN8Presonus7Surface14SLMixerHandlerD1Ev");
extern "C" void destroyD2(E *) asm("_ZN8Presonus7Surface14SLMixerHandlerD2Ev");
extern "C" void colorBaseD1(Presonus::IColorConverter *) asm(
    "_ZN8Presonus15IColorConverterD1Ev");
extern "C" void colorBaseD0(Presonus::IColorConverter *) asm(
    "_ZN8Presonus15IColorConverterD0Ev");
static unsigned packed(Core::Color c) {
  return unsigned(c.red) | unsigned(c.green) << 8 | unsigned(c.blue) << 16 |
         unsigned(c.alpha) << 24;
}
int main(int argc, char **argv) {
  if (argc < 2)
    return 2;
  std::string mode = argv[1];
  MixerColorConverter converter;
  if (mode == "name") {
    std::cout << packed(Presonus::ColorMapping::mapColor(
                     argc > 2 && std::strcmp(argv[2], "<NULL>") ? argv[2]
                                                                : nullptr))
              << '\n';
  } else if (mode == "index") {
    std::cout << packed(converter.getRGBFromColorIndex(std::stoi(argv[2])))
              << '\n';
  } else if (mode == "rgb") {
    unsigned c = std::stoul(argv[2]);
    std::cout << converter.getColorIndexForRGB(Core::Color(
                     c & 255, (c >> 8) & 255, (c >> 16) & 255, c >> 24))
              << '\n';
  } else if (mode == "colorlife") {
    int variant = std::stoi(argv[2]);
    auto *p = new MixerColorConverter;
    watched[0] = p;
    capture = true;
    if (variant == 0)
      delete static_cast<Presonus::IColorConverter *>(p);
    else if (variant == 2)
      colorBaseD1(p);
    else if (variant == 3)
      colorBaseD0(p);
    else {
      p->~MixerColorConverter();
    }
    capture = false;
    std::cout << total << '\n';
    if (variant == 1 || variant == 2)
      ::operator delete(p);
  } else if (mode == "life") {
    int variant = std::stoi(argv[2]), mask = std::stoi(argv[3]);
    Presonus::Surface::EQPageComponent eq;
    Presonus::Surface::GeqPageComponent geq;
    Core::Portable::ParamInfo info{};
    Core::Portable::NumericParam first(info), second(info);
    auto *color = (mask & 4) ? new MixerColorConverter : nullptr;
    class OtherObserver
        : public Presonus::Surface::EQPageComponent::IObserver,
          public Presonus::Surface::GeqPageComponent::IObserver {
    public:
      void onEqEncoderModeChanged() override { std::abort(); }
      void onGeqScrollOffsetChanged() override { std::abort(); }
    } left, right;
    if (mask & 1)
      eq.addObserver(&left);
    if (mask & 2)
      geq.addObserver(&left);
    auto *p = new Fixture((mask & 1) ? &eq : nullptr,
                          (mask & 2) ? &geq : nullptr, color);
    if (mask & 1)
      eq.addObserver(&right);
    if (mask & 2)
      geq.addObserver(&right);
    if (mask & 8)
      p->setDigitalParams(&first, (mask & 16) ? &first : &second);
    if (mask & 32) {
      auto *owned = new Core::Portable::NumericParam(info);
      X::lifecycleParameters(*p).add(owned);
      watched[5] = owned;
      watched[11] =
          static_cast<Core::Portable::Parameter **>(X::lifecycleParameters(*p));
      X::lifecycleComponents(*p).add(nullptr);
      X::lifecycleFirstFlags(*p).add(true);
      X::lifecycleSecondFlags(*p).add(false);
      watched[2] = static_cast<bool *>(X::lifecycleSecondFlags(*p));
      watched[3] = static_cast<bool *>(X::lifecycleFirstFlags(*p));
      watched[4] =
          static_cast<Core::Portable::Component **>(X::lifecycleComponents(*p));
    }
    watched[0] = color;
    watched[1] = p;
    capture = true;
    if (variant == 0)
      destroyD0(p);
    else if (variant == 1)
      destroyD1(p);
    else
      destroyD2(p);
    capture = false;
    // Real provider operations after destruction must not call the dead
    // observer.
    first.changed();
    second.changed();
    std::cout << "{\"eq\":" << A::observers(eq).count()
              << ",\"geq\":" << A::observers(geq).count()
              << ",\"removed\":" << removals << ",\"freed\":[";
    for (int i = 0; i < total; ++i) {
      if (i)
        std::cout << ',';
      std::cout << freed[i];
    }
    std::cout << "],\"cleanup\":[";
    for (int i = 0; i < cleanupTotal; ++i) {
      if (i)
        std::cout << ',';
      std::cout << cleanup[i];
    }
    std::cout << "]}\n";
    if (variant)
      ::operator delete(p);
  } else if (mode == "compat") {
    Fixture p;
    // Deliberately invalid opaque borrowed page identity remains unowned.
    X::geqPage(p) = reinterpret_cast<Presonus::PageComponent *>(1);
    std::cout << 0 << '\n';
  } else
    return 2;
}
