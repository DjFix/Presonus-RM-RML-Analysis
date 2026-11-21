#include "presonus/application/ResourceLibrary.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/noaa/card.hpp"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/status_property.hpp"
#include <cstdlib>
#include <iostream>
#include <string>
using namespace Presonus::NOAA;
using namespace presonus::noaa;
struct Response final : presonus::dice::ResponseServices {
  std::int64_t clockRawTicks() override { std::abort(); }
  void pumpIdle(bool) override { std::abort(); }
  void sleepMilliseconds(std::uint32_t) override { std::abort(); }
  void timeoutNotice(bool, std::uint32_t, std::uint32_t) override {
    std::abort();
  }
};
struct IO final : SpiServiceIO {
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int, const SpiTransfer &) override { std::abort(); }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { std::abort(); }
  void diagnostic(bool, const char *, int, bool) override { std::abort(); }
};
struct Card final : TCard {
  Card(CardState &s, Response &r, IO &i) : TCard(cardSetupTag, s, r, i) {}
  std::int32_t updateFirmware(Presonus::UC::IFirmwareUpdateListener *,
                              int) override {
    std::abort();
  }
};
struct Handler final : TCardHandler {
  Handler(CardHandlerState &s, Response &r)
      : TCardHandler(cardHandlerSetupTag, s, r) {}
  int calls = 0;
  void getProperty(Core::Property &property) override {
    if (property.type != NOAAStatusProperty::kID)
      std::abort();
    ++calls;
    TCardHandler::getProperty(property);
  }
  void setProperty(const Core::Property &) override { std::abort(); }
  void release() override { std::abort(); }
  int threadEntry() override { std::abort(); }
};

int main(int argc, char **argv) {
  if (argc != 5)
    return 2;
  const bool bound = std::stoi(argv[1]) != 0;
  const int inputFirst = std::stoi(argv[2]);
  const int inputSecond = std::stoi(argv[3]);
  const bool alias = std::stoi(argv[4]) != 0;
  Presonus::ResourceLibrary resources;
  CardState cardState{};
  cardState.resources = &resources;
  cardState.observedWord3c = static_cast<std::uint32_t>(inputFirst);
  cardState.observedWord34 = static_cast<std::uint32_t>(inputSecond);
  Response response;
  IO io;
  Card card(cardState, response, io);
  std::array<unsigned char, 52> seed;
  seed.fill(0xa7);
  NOAAStatusProperty status(seed);
  CardHandlerState state{card};
  state.statusProperty = &status;
  Handler handler(state, response);
  Presonus::Mixer::MixerComponentBase mixer;
  if (bound) {
    mixer.digitalRouteHandler = &handler;
    mixer.serialStatus = &status;
  }
  int first = -3, second = -9;
  mixer.getMixerSerialInfo(first, alias ? first : second);
  if (status.payload != seed)
    return 3;
  std::cout << "serial " << first << ' ' << second << ' ' << handler.calls
            << '\n';
}
