#include "core/system/coredebug.h"
#include "presonus/mixer/DigitalInputComponent.hpp"
#include "presonus/mixer/RackMixerComponent.hpp"
#include "presonus/noaa/card.hpp"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/router.hpp"
#include <array>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cxxabi.h>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <unordered_map>
#include <vector>
static bool recording;
static const void *volatile castObservation;
static std::ostringstream trace;
static std::unordered_map<const void *, int> channelIds, paramIds;
extern "C" Core::Portable::Parameter *
__real__ZNK4Core8Portable9Component17getParameterByTagEi(
    const Core::Portable::Component *, int);
extern "C" Core::Portable::Parameter *
__wrap__ZNK4Core8Portable9Component17getParameterByTagEi(
    const Core::Portable::Component *p, int tag) {
  if (recording)
    trace << "G:" << channelIds.at(p) << ':' << tag << ';';
  return __real__ZNK4Core8Portable9Component17getParameterByTagEi(p, tag);
}
extern "C" void
__real__ZN4Core8Portable9Parameter7changedEv(Core::Portable::Parameter *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter7changedEv(Core::Portable::Parameter *p) {
  if (recording)
    trace << "X:" << paramIds.at(p) << ';';
  __real__ZN4Core8Portable9Parameter7changedEv(p);
}
extern "C" void *__real___dynamic_cast(const void *,
                                       const __cxxabiv1::__class_type_info *,
                                       const __cxxabiv1::__class_type_info *,
                                       std::ptrdiff_t);
extern "C" void *__wrap___dynamic_cast(const void *p,
                                       const __cxxabiv1::__class_type_info *s,
                                       const __cxxabiv1::__class_type_info *d,
                                       std::ptrdiff_t hint) {
  if (recording && channelIds.count(p))
    trace << "T:" << channelIds.at(p) << ';';
  return __real___dynamic_cast(p, s, d, hint);
}
struct Watch final : Core::Portable::IParamObserver {
  int count{};
  void *castTo(TypeID t) override {
    return t == IParamObserver::kTypeID ? static_cast<IParamObserver *>(this)
                                        : nullptr;
  }
  void paramChanged(Core::Portable::Parameter *, int) override { ++count; }
};

extern "C" void __real__ZN4Core11DebugPrintfEPKcz(const char *, ...);
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  va_list args;
  va_start(args, format);
  va_list copy;
  va_copy(copy, args);
  if (recording && std::strcmp(format, "**************** micline #%d\n") == 0)
    trace << "D:" << va_arg(copy, int) << ';';
  va_end(copy);
  char text[1024];
  std::vsnprintf(text, sizeof(text), format, args);
  va_end(args);
  __real__ZN4Core11DebugPrintfEPKcz("%s", text);
}
struct Response final : presonus::dice::ResponseServices {
  std::int64_t clockRawTicks() override { std::abort(); }
  void pumpIdle(bool) override { std::abort(); }
  void sleepMilliseconds(std::uint32_t) override { std::abort(); }
  void timeoutNotice(bool, std::uint32_t, std::uint32_t) override {
    std::abort();
  }
};
struct IO final : presonus::noaa::SpiServiceIO {
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int, const presonus::noaa::SpiTransfer &) override {
    std::abort();
  }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { std::abort(); }
  void diagnostic(bool, const char *, int, bool) override { std::abort(); }
};
struct Router final : Presonus::NOAA::TCardRouter {
  Router(presonus::noaa::RouterState &s, Response &r, IO &io)
      : TCardRouter(s, r, io,
                    presonus::noaa::rm13731LinkAddressRouterLookup()) {}
  void post(Presonus::NOAA::SysexPacket &) override { std::abort(); }
};
struct Handler final : Presonus::NOAA::TCardHandler {
  Handler(presonus::noaa::CardHandlerState &s, Response &r)
      : TCardHandler(presonus::noaa::cardHandlerSetupTag, s, r) {}
  void setProperty(const Core::Property &property) override {
    auto *projection = portableHandlerState().immediate;
    if (!projection || projection->property != &property ||
        property.type != 0x64746e70 || property.size != 24)
      throw std::logic_error("invalid live property projection");
    if (recording) {
      trace << "E:" << static_cast<unsigned>(property.type) << ':'
            << property.size;
      for (int i = 0; i < 4; ++i)
        trace << ':' << projection->words[i];
      trace << ';';
    }
    TCardHandler::setProperty(property);
  }
};
int main(int argc, char **argv) {
  bool provider = argc == 2 && std::string(argv[1]) == "--provider";
  unsigned first, aux, fx;
  int inputs;
  while (std::cin >> first >> aux >> fx >> inputs) {
    if (first > 32 || fx > 4)
      throw std::logic_error("outside valid portable collection domain");
    recording = false;
    trace.str("");
    trace.clear();
    channelIds.clear();
    paramIds.clear();
    std::array<Core::Portable::ParamInfo, 4> infos;
    std::array<Watch, 4> watches;
    std::array<Presonus::Mixer::ChannelComponent *, 4> channels{};
    std::array<Core::Portable::Parameter *, 4> params{};
    std::vector<std::unique_ptr<Presonus::Mixer::ChannelComponent>> objects;
    Core::Vector<Presonus::Mixer::ChannelComponent *> candidates, sources;
    Core::Vector<Presonus::Mixer::FXComponent *> effects;
    for (unsigned i = 0; i < first; ++i)
      sources.add(nullptr);
    for (unsigned i = 0; i < fx; ++i)
      effects.add(nullptr);
    for (int i = 0; i < inputs; ++i) {
      int kind, present;
      std::cin >> kind >> present;
      if (!kind) {
        candidates.add(nullptr);
        continue;
      }
      std::unique_ptr<Presonus::Mixer::ChannelComponent> channel;
      if (kind == 2)
        channel = std::make_unique<Presonus::Mixer::DigitalInputComponent>(
            Presonus::Mixer::ChannelComponent::SourcePortConstruction{});
      else
        channel = std::make_unique<Presonus::Mixer::ChannelComponent>(
            Presonus::Mixer::ChannelComponent::SourcePortConstruction{});
      channels[i] = channel.get();
      channelIds[static_cast<Core::Portable::Component *>(channel.get())] = i;
      if (present) {
        infos[i] = PARAM_FLOAT(360, "digital", 0.f, 1.f, 0.f, .01f, nullptr,
                               nullptr, 0.f, 0);
        channel->addParameters(&infos[i], 1);
        params[i] = channel->getParameterByTag(360);
        paramIds[params[i]] = i;
        params[i]->addObserver(&watches[i]);
      }
      candidates.add(channel.get());
      objects.push_back(std::move(channel));
    }
    Response response;
    IO io;
    presonus::noaa::CardState cardState{};
    cardState.observedWord14 = 2;
    Presonus::NOAA::TCard card(presonus::noaa::cardSetupTag, cardState,
                               response, io);
    presonus::noaa::RouterState routerState{};
    routerState.applicationBytes.fill(0);
    routerState.slotTables = &presonus::noaa::rm13731GambitRouterSlots();
    Router router(routerState, response, io);
    presonus::noaa::CardHandlerState handlerState{card};
    handlerState.router = &router;
    Handler handler(handlerState, response);
    Core::Property sentinel(0, 8);
    presonus::noaa::ImmediatePropertyProjection previous{&sentinel};
    handlerState.immediate = &previous;
    Presonus::Mixer::MixerComponentBase base;
    std::uint32_t cascade = 0;
    Presonus::Mixer::RackMixerComponent rack(base, cascade);
    rack.danteSourceChannels = &sources;
    rack.danteEffects = &effects;
    rack.digitalInputCandidates = &candidates;
    rack.danteHandler = &handler;
    std::memcpy(&rack.auxiliaryRouteCount, &aux, 4);
    recording = true;
    if (!provider)
      rack.setDanteStaticRoutes();
    else {
      int count;
      std::cin >> count;
      for (int i = 0; i < count; ++i) {
        int code;
        std::cin >> code;
        if (code == 0) {
          unsigned n;
          std::cin >> n;
          Core::DebugPrintf("**************** micline #%d\n",
                            static_cast<int>(n));
        } else if (code == 1) {
          std::array<unsigned, 6> w;
          for (auto &v : w)
            std::cin >> v;
          Core::Property property(static_cast<int>(w[0]),
                                  static_cast<int>(w[1]));
          presonus::noaa::ImmediatePropertyProjection projection{
              &property, {w[2], w[3], w[4], w[5], 0}};
          auto *old = handlerState.immediate;
          handlerState.immediate = &projection;
          handler.setProperty(property);
          handlerState.immediate = old;
        } else if (code == 2) {
          int id;
          std::cin >> id;
          castObservation =
              dynamic_cast<Presonus::Mixer::DigitalInputComponent *>(
                  channels[id]);
        } else if (code == 3) {
          int id, tag;
          std::cin >> id >> tag;
          (void)channels[id]->getParameterByTag(tag);
        } else if (code == 4) {
          int id;
          std::cin >> id;
          params[id]->changed();
        } else
          throw std::logic_error("bad provider schedule");
      }
    }
    recording = false;
    if (handlerState.immediate != &previous)
      throw std::logic_error("dangling immediate projection");
    std::cout << "RESULT " << trace.str() << '|';
    static const char hex[] = "0123456789abcdef";
    for (auto byte : routerState.applicationBytes)
      std::cout << hex[byte >> 4] << hex[byte & 15];
    std::cout << '|';
    for (int i = 0; i < 4; ++i) {
      std::cout << watches[i].count << ' ';
      if (params[i])
        params[i]->removeObserver(&watches[i]);
    }
    std::cout << '\n';
  }
}
