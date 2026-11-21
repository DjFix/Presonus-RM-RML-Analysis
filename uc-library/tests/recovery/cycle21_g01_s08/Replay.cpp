#include "core/portable/coreparams.h"
#include "presonus/mixer/RackMixerComponent.hpp"
#include "presonus/noaa/card.hpp"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/router.hpp"
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

using namespace Presonus::Mixer;
using namespace Presonus::NOAA;
using namespace Core::Portable;

namespace {
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
struct Router final : TCardRouter {
  Router(presonus::noaa::RouterState &state, Response &response, IO &io)
      : TCardRouter(state, response, io,
                    presonus::noaa::rm13731LinkAddressRouterLookup()) {}
  void post(SysexPacket &) override { std::abort(); }
};
struct Handler final : TCardHandler {
  Handler(presonus::noaa::CardHandlerState &state, Response &response)
      : TCardHandler(presonus::noaa::cardHandlerSetupTag, state, response) {}
  void setProperty(const Core::Property &property) override {
    auto *projection = portableHandlerState().immediate;
    if (!projection || projection->property != &property)
      std::abort();
    std::cout << "property:" << property.type << ':' << property.size;
    for (int i = 0; i < (property.size - 8) / 4; ++i)
      std::cout << ':' << projection->words[i];
    std::cout << '\n';
    TCardHandler::setProperty(property);
  }
};
class ObservedValue : public NumericParam {
public:
  ObservedValue(const ParamInfo &info, float value)
      : NumericParam(info), value(value) {}
  ParamValue getValue() const override {
    std::cout << "value:23\n";
    return value;
  }

private:
  float value;
};
class Settings : public Component {
public:
  void add(ObservedValue *parameter) { paramList.add(parameter); }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 8)
    return 2;
  const int output = std::stoi(argv[2]);
  const int selection = std::stoi(argv[3]);
  const bool rack = argv[4][0] == '1';
  const int count = std::stoi(argv[5]);
  Response response;
  IO io;
  presonus::noaa::CardState cardState{};
  TCard card(presonus::noaa::cardSetupTag, cardState, response, io);
  presonus::noaa::RouterState routerState{};
  routerState.applicationBytes.fill(0);
  Router router(routerState, response, io);
  presonus::noaa::CardHandlerState handlerState{card};
  handlerState.router = &router;
  Handler handler(handlerState, response);
  const Core::Property sentinel(0, 8);
  const presonus::noaa::ImmediatePropertyProjection old{&sentinel};
  handlerState.immediate = &old;

  ParamInfo info{};
  info.tag = 23;
  Settings settings;
  if (std::string(argv[6]) != "none")
    settings.add(new ObservedValue(info, std::stof(argv[6])));
  MixerComponentBase mixer;
  mixer.sceneSettings = &settings;
  mixer.digitalRouteHandler = &handler;
  mixer.tdmConfigWord = 4;
  mixer.digitalOutputRouteDirty = argv[7][0] == '1';
  std::uint32_t cascade = 0;
  RackMixerComponent rackRoutes(mixer, cascade);
  if (rack)
    mixer.rackDigitalRoutes = &rackRoutes;
  Core::Vector<ChannelComponent *> sipChannels;
  for (int i = 0; i < count; ++i)
    sipChannels.add(nullptr);
  mixer.sipSoloChannels = &sipChannels;
  mixer.routeDigitalOutput(output, selection);
  std::cout << "dirty:" << mixer.digitalOutputRouteDirty << '\n';
  // Both real property handlers enqueue two offline route writes for these
  // supported fixture selections; the previous projection must survive.
  return handlerState.immediate == &old &&
                 routerState.applicationBytes[0x118 - 0x18] == 1 &&
                 routerState.applicationBytes[0x11c - 0x18] == 2
             ? 0
             : 1;
}
